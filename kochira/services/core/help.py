"""
Help and documentation.

This service displays help information on the web server.

Commands
========

Help
----

::

    $bot: help
    $bot: help me!
    !help
    !commands

Links the user to the web help service, if available.
"""

from kochira import config
from kochira.service import Service
from docutils.core import publish_parts
from tornado.web import RequestHandler, Application, HTTPError, UIModule

service = Service(__name__, __doc__)

@service.config
class Config(config.Config):
    url = config.Field(doc="Base URL for the help documentation, e.g. ``http://example.com:8000/help``.")


class RequestHandler(RequestHandler):
    def render(self, name, **kwargs):
        return super().render(name,
                              rst=lambda s, **kw: publish_parts(s, writer_name="html", **kw)["fragment"],
                              **kwargs)

class IndexHandler(RequestHandler):
    def get(self):
        services = [service for service, _ in self.application.bot.services.values()]
        services.sort(key=lambda s: s.name)

        self.render("help/index.html", services=services)


class ServiceHelpHandler(RequestHandler):
    def get(self, service_name):
        try:
            service, _ = self.application.bot.services[service_name]
        except KeyError:
            raise HTTPError(404)
        self.render("help/service.html", service=service)


class ConfigModule(UIModule):
    def render(self, cfg):
        return self.render_string("help/_modules/config.html",
                                  config=cfg, ConfigType=config.Config)


def make_application(settings):
    settings = settings.copy()
    settings["ui_modules"]["Config"] = ConfigModule

    return Application([
        (r"/", IndexHandler),
        (r"/(.*)", ServiceHelpHandler)
    ], **settings)


@service.hook("services.net.webserver", priority=-9999)
def webserver_config(bot):
    return {
        "name": "help",
        "title": "Help",
        "application_factory": make_application
    }


@service.command(r"!commands")
@service.command(r"!help")
@service.command(r"help(?: me)?!?$", mention=True)
def help(client, target, origin):
    config = service.config_for(client.bot)

    if "kochira.services.net.webserver" not in client.bot.services:
        client.message(target, "{origin}: Help currently unavailable.".format(
            origin=origin
        ))
    else:
        client.message(target, "{origin}: My help is available at {url}".format(
            origin=origin,
            url=config.url
        ))
