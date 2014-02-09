"""
Administration services.

This service allows administrators to manage various aspects of the bot.
"""

from io import StringIO
import os
import signal
import subprocess
import sys

from kochira.auth import requires_permission, ACLEntry
from kochira.service import Service

service = Service(__name__, __doc__)


@service.setup
def setup_eval_locals(bot):
    storage = service.storage_for(bot)
    storage.eval_locals = {}


@service.command(r"grant (?P<permission>\S+) to (?P<hostmask>\S+)(?: on channel (?P<channel>\S+))?\.?$", mention=True)
@requires_permission("admin")
def grant(client, target, origin, permission, hostmask, channel=None):
    """
    Grant permission.

    ::

        $bot: grant <permission> to <hostmask>
        $bot: grant <permission> to <hostmask> on channel <channel>

    **Requires permission:** admin

    Grant a permission to the given hostmask. It can be done on a channel-specific
    basis. Wildcard hostmasks are permitted.
    """

    ACLEntry.grant(client.network, hostmask, permission, channel)

    if channel is not None:
        message = "Granted permission \"{permission}\" to {hostmask} on channel {channel} for network \"{network}\".".format(
            permission=permission,
            hostmask=hostmask,
            channel=channel,
            network=client.network
        )
    else:
        message = "Granted permission \"{permission}\" to {hostmask} globally for network \"{network}\".".format(
            permission=permission,
            hostmask=hostmask,
            network=client.network
        )

    client.message(target, message)


@service.command(r"revoke (?P<permission>\S+) from (?P<hostmask>\S+)(?: on channel (?P<channel>\S+))?\.?$", mention=True)
@requires_permission("admin")
def revoke(client, target, origin, permission, hostmask, channel=None):
    """
    Revoke permission.

    ::

        $bot: revoke <permission> from <hostmask>
        $bot: revoke <permission> from <hostmask> on channel <channel>

    **Requires permission:** admin

    Revoke a permission from the given hostmask. It can be done on a
    channel-specific basis. Wildcard hostmasks are permitted and will revoke
    permissions for any hostmask matching it.
    """

    if permission == "everything":
        permission = None

    ACLEntry.revoke(client.network, hostmask, permission, channel)

    if permission is None:
        message_part = "all permissions"
    else:
        message_part = "permission \"{permission}\"".format(permission=permission)

    if channel is not None:
        message = "Revoked {message_part} from {hostmask} on channel {channel} for network \"{network}\".".format(
            message_part=message_part,
            hostmask=hostmask,
            channel=channel,
            network=client.network
        )
    else:
        message = "Revoked {message_part} from {hostmask} globally for network \"{network}\".".format(
            message_part=message_part,
            hostmask=hostmask,
            network=client.network
        )

    client.message(target, message)


@service.command(r"(?P<r>re)?load service (?P<service_name>\S+)$", mention=True)
@requires_permission("admin")
def load_service(client, target, origin, r, service_name):
    """
    Load service.

    ::

        $bot: load service <name>
        $bot: reload service <name>

    **Requires permission:** admin

    Load or reload a service with the given name. Reloading will force all code to
    be reloaded.
    """

    try:
        try:
            client.bot.load_service(service_name, r is not None)
        except ImportError:
            service_name = service.SERVICES_PACKAGE + '.' + service_name
            client.bot.load_service(service_name, r is not None)
    except Exception as e:
        client.message(target, "Sorry, couldn't load the service \"{name}\".".format(
            name=service_name
        ))
        client.message(target, "↳ {name}: {info}".format(
            name=e.__class__.__name__,
            info=str(e)
        ))
        return

    if r is not None:
        message = "Reloaded service \"{name}\".".format(name=service_name)
    else:
        message = "Loaded service \"{name}\".".format(name=service_name)

    client.message(target, message)


@service.command(r"unload service (?P<service_name>\S+)$", mention=True)
@requires_permission("admin")
def unload_service(client, target, origin, service_name):
    """
    Unload service.

    ::

        $bot: unload service <name>

    **Requires permission:** admin

    Unload a currently running service.
    """

    if service_name not in client.bot.services:
        service_name = service.SERVICES_PACKAGE + '.' + service_name
    try:
        client.bot.unload_service(service_name)
    except Exception as e:
        client.message(target, "Sorry, couldn't unload the service \"{name}\".".format(
            name=service_name
        ))
        client.message(target, "↳ {name}: {info}".format(
            name=e.__class__.__name__,
            info=str(e)
        ))
        return

    client.message(target, "Unloaded service \"{name}\".".format(name=service_name))


@service.command(r"what services are(?: you)? running\??$", mention=True)
@service.command(r"(?:list )?services$", mention=True)
@requires_permission("admin")
def list_services(client, target, origin):
    """
    List services.

    ::

        $bot: services
        $bot: list services

    **Requires permission:** admin

    List all running services.
    """

    client.message(target, "I am running: {services}".format(
        services=", ".join(client.bot.services))
    )


@service.command(r"reload(?: all)? services$", mention=True)
@requires_permission("admin")
def reload_services(client, target, origin):
    failed_services = []

    for service_name in list(client.bot.services.keys()):
        try:
            client.bot.load_service(service_name, True)
        except:
            failed_services.append(service_name)

    if failed_services:
        client.message(target, "I couldn't reload the following services: {failed_services}".format(
            failed_services=", ".join(failed_services))
        )
    else:
        client.message(target, "All services reloaded!")


@service.command(r">>> (?P<code>.+)$")
@service.command(r"eval (?P<code>.+)$", mention=True)
@requires_permission("admin")
def eval_code(client, target, origin, code):
    """
    Evaluate code.

    ::

        $bot: eval <code>
        >>> <code>

    **Requires permission:** admin

    Evaluate code inside the bot. The local ``bot`` is provided for access to
    bot internals.
    """

    storage = service.storage_for(client.bot)

    buf = StringIO()
    sys.stdout = buf

    try:
        eval(compile(code, "<irc>", "single"),
             {"bot": client.bot}, storage.eval_locals)
    except BaseException as e:
        client.message(target, "<<! {name}: {info}".format(
            name=e.__class__.__name__,
            info=str(e)
        ))
        return
    finally:
        sys.stdout = sys.__stdout__

    output = buf.getvalue().rstrip("\n")

    if output:
        for line in output.split("\n"):
            client.message(target, "<<< {}".format(line))
    else:
        client.message(target, "(no result)")


@service.command(r"rehash$", mention=True)
@requires_permission("admin")
def rehash(client, target, origin):
    """
    Rehash configuration.

    ::

        $bot: rehash

    **Requires permission:** admin

    Rehash the bot's configuration settings.
    """

    try:
        client.bot.rehash()
    except BaseException as e:
        client.message(target, "Sorry, couldn't rehash.")
        client.message(target, "↳ {name}: {info}".format(
            name=e.__class__.__name__,
            info=str(e)
        ))
        return

    client.message(target, "Configuration rehashed.")


@service.command(r"re(?:start|boot)$", mention=True)
@requires_permission("admin")
def restart(client, target, origin):
    """
    Restart.

    ::

        $bot: restart
        $bot: reboot

    **Requires permission:** admin

    Restart the bot. Will ``exec`` a new process into the currently running process
    space.
    """

    for client in list(client.bot.networks.values()):
        client.quit("Restarting...")

    # The following code is ported from Tornado.
    # http://www.tornadoweb.org/en/branch2.4/_modules/tornado/autoreload.html

    if hasattr(signal, "setitimer"):
        # Clear the alarm signal set by
        # ioloop.set_blocking_log_threshold so it doesn't fire
        # after the exec.
        signal.setitimer(signal.ITIMER_REAL, 0, 0)
    # sys.path fixes: see comments at top of file.  If sys.path[0] is an empty
    # string, we were (probably) invoked with -m and the effective path
    # is about to change on re-exec.  Add the current directory to $PYTHONPATH
    # to ensure that the new process sees the same path we did.
    path_prefix = '.' + os.pathsep
    if (sys.path[0] == '' and
        not os.environ.get("PYTHONPATH", "").startswith(path_prefix)):
        os.environ["PYTHONPATH"] = (path_prefix +
                                    os.environ.get("PYTHONPATH", ""))
    if sys.platform == 'win32':
        # os.execv is broken on Windows and can't properly parse command line
        # arguments and executable name if they contain whitespaces. subprocess
        # fixes that behavior.
        subprocess.Popen([sys.executable] + sys.argv)
        sys.exit(0)
    else:
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except OSError:
            # Mac OS X versions prior to 10.6 do not support execv in
            # a process that contains multiple threads.  Instead of
            # re-executing in the current process, start a new one
            # and cause the current process to exit.  This isn't
            # ideal since the new process is detached from the parent
            # terminal and thus cannot easily be killed with ctrl-C,
            # but it's better than not being able to autoreload at
            # all.
            # Unfortunately the errno returned in this case does not
            # appear to be consistent, so we can't easily check for
            # this error specifically.
            os.spawnv(os.P_NOWAIT, sys.executable,
                      [sys.executable] + sys.argv)
            sys.exit(0)
