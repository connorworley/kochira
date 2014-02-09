import logging
from collections import deque
from pydle import Client as _Client

logger = logging.getLogger(__name__)


class Client(_Client):
    def __init__(self, bot, network, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.backlogs = {}
        self.bot = bot

        # set network name to whatever we have in our config
        self.network = network

    def _send_message(self, message):
        self.bot.defer_from_thread(super()._send_message, message)

    def on_ctcp_version(self, by, target, message):
        self.ctcp_reply(by, "VERSION",
                        self.bot.config.core.version)

    def on_connect(self):
        logger.info("Connected to IRC network: %s", self.network)
        super().on_connect()

    def message(self, target, message):
        super().message(target, message)
        self.bot.defer_from_thread(self.bot.run_hooks,
                                   "own_message", self, target, message)

    def on_channel_message(self, target, origin, message):
        backlog = self.backlogs.setdefault(target, deque([]))
        backlog.appendleft((origin, message))

        while len(backlog) > self.bot.config.core.max_backlog:
            backlog.pop()

    def on_private_message(self, origin, message):
        backlog = self.backlogs.setdefault(origin, deque([]))
        backlog.appendleft((origin, message))

        while len(backlog) > self.bot.config.core.max_backlog:
            backlog.pop()

    def __getattribute__(self, name):
        if name.startswith("on_"):
            # automatically generate a hook runner for all on_ functions
            hook_name = name[3:]

            try:
                f = _Client.__getattribute__(self, name)
            except AttributeError:
                def _magic_hook(*args, **kwargs):
                    self.bot.run_hooks(hook_name, self, *args, **kwargs)
            else:
                def _magic_hook(*args, **kwargs):
                    r = f(*args, **kwargs)
                    self.bot.run_hooks(hook_name, self, *args, **kwargs)
                    return r

            return _magic_hook
        else:
            return _Client.__getattribute__(self, name)
