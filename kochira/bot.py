from concurrent.futures import ThreadPoolExecutor
import functools
import imp
import importlib
import heapq
import logging
import multiprocessing
from peewee import SqliteDatabase
import signal
import yaml
from zmq.eventloop import ioloop

from .auth import ACLEntry
from .client import Client
from .db import database
from .scheduler import Scheduler
from .util import Expando
from .service import Service

logger = logging.getLogger(__name__)


class Bot:
    """
    The core bot.
    """

    def __init__(self, config_file="config.yml"):
        self.services = {}
        self.networks = {}
        self.io_loop = ioloop.IOLoop()

        self.config_file = config_file

        self.rehash()
        self._connect_to_db()

    def run(self):
        self.executor = ThreadPoolExecutor(multiprocessing.cpu_count())
        self.scheduler = Scheduler(self)
        self.scheduler.start()

        signal.signal(signal.SIGHUP, self._handle_sighup)

        self._load_services()
        self._connect_to_irc()

    def connect(self, network_name):
        config = self.config["networks"][network_name]

        tls_config = config.get("tls", {})
        sasl_config = config.get("sasl", {})

        client = Client(self, network_name, config["nickname"],
            username=config.get("username", None),
            realname=config.get("realname", None),
            tls_client_cert=tls_config.get("certificate_file"),
            tls_client_cert_key=tls_config.get("certificate_keyfile"),
            tls_client_cert_password=tls_config.get("certificate_password"),
            sasl_username=sasl_config.get("username"),
            sasl_password=sasl_config.get("password")
        )

        client.connect(
            hostname=config["hostname"],
            password=config.get("password"),
            source_address=(config["source_address"], 0) if "source_address" in config else None,
            port=config.get("port"),
            tls=tls_config.get("enabled", False),
            tls_verify=tls_config.get("verify", True)
        )

        self.networks[network_name] = client

        def handle_next_message(fd=None, events=None):
            if client._has_message():
                client.poll_single()
                self.io_loop.add_callback(handle_next_message)

        self.io_loop.add_handler(client.connection.socket.fileno(),
                                 handle_next_message,
                                 ioloop.IOLoop.READ)

        return client

    def disconnect(self, network_name):
        client = self.networks[network_name]
        fileno = client.connection.socket.fileno()
        self.io_loop.remove_handler(fileno)

        try:
            client.quit()
        finally:
            del self.networks[network_name]

    def _connect_to_db(self):
        db_name = self.config["core"].get("database", "kochira.db")
        database.initialize(SqliteDatabase(db_name, threadlocals=True))
        logger.info("Opened database connection: %s", db_name)

        ACLEntry.create_table(True)

    def _connect_to_irc(self):
        for network_name, config in self.config["networks"].items():
            if config.get("autoconnect", False):
                self.connect(network_name)

        self.io_loop.start()

    def _load_services(self):
        for service, config in self.config["services"].items():
            if config.get("autoload"):
                try:
                    self.load_service(service)
                except:
                    pass # it gets logged

    def _shutdown_service(self, service):
        service.run_shutdown(self)
        self.scheduler.unschedule_service(service)

    def defer_from_thread(self, fn, *args, **kwargs):
        self.io_loop.add_callback(functools.partial(fn, *args, **kwargs))

    def load_service(self, name, reload=False):
        """
        Load a service into the bot.

        The service should expose a variable named ``service`` which is an
        instance of ``kochira.service.Service`` and configured appropriately.
        """

        # ensure that the service's shutdown routine is run
        if name in self.services:
            service, _ = self.services[name]
            self._shutdown_service(service)

        # we create an expando storage first for bots to load any locals they
        # need
        service = None
        storage = Expando()

        try:
            module = importlib.import_module(name)

            if reload:
                module = imp.reload(module)

            if not hasattr(module, "service"):
                raise RuntimeError("{} is not a valid service".format(name))

            service = module.service
            self.services[service.name] = (service, storage)

            service.run_setup(self)
        except:
            logger.error("Couldn't load service %s", name, exc_info=True)
            if service is not None:
                del self.services[service.name]
            raise

        logger.info("Loaded service %s", name)

    def unload_service(self, name):
        """
        Unload a service from the bot.
        """
        service, _ = self.services[name]
        self._shutdown_service(service)
        del self.services[name]

    def get_hooks(self, hook):
        """
        Create an ordering of hooks to run.
        """

        return (hook for _, _, hook in heapq.merge(*[
            service.hooks.get(hook, [])
            for service, storage in list(self.services.values())
        ]))

    def run_hooks(self, hook, *args):
        """
        Attempt to dispatch a command to all command handlers.
        """

        for hook in self.get_hooks(hook):
            try:
                r = hook(*args)
                if r is Service.EAT:
                    return Service.EAT
            except BaseException:
                logger.error("Hook processing failed", exc_info=True)

    def rehash(self):
        """
        Reload configuration information.
        """

        with open(self.config_file, "r") as f:
            self.config = yaml.load(f)

    def _handle_sighup(self, signum, frame):
        logger.info("Received SIGHUP; running SIGHUP hooks and rehashing")

        try:
            self.rehash()
        except Exception as e:
            logger.error("Could not rehash configuration", exc_info=e)

        self.run_hooks("sighup", self)
