"""
Automatic replies for keywords.

This service enables the bot to respond to predefined replies specified by
users.
"""

import random
import re
from peewee import CharField

from kochira.db import Model

from kochira.service import Service
from kochira.auth import requires_permission

service = Service(__name__, __doc__)

class Reply(Model):
    what = CharField(255)
    reply = CharField(255)

    class Meta:
        indexes = (
            (("what",), True),
        )


def is_regex(what):
    return what[0] == "/" and what[-1] == "/"


@service.setup
def initialize_model(bot):
    Reply.create_table(True)


@service.command(r"stop replying to (?P<what>.+)$", mention=True)
@service.command(r"don't reply to (?P<what>.+)$", mention=True)
@service.command(r"remove reply (?:to|for) (?P<what>.+)$", mention=True)
@requires_permission("reply")
def remove_reply(client, target, origin, what):
    """
    Remove reply.

    ::

        $bot: stop replying to <what>
        $bot: don't reply to <what>
        $bot: remove reply (to|for) <what>

    **Requires permission:** reply

    Remove the reply for `what`.
    """

    if not Reply.select().where(Reply.what == what).exists():
        client.message(target, "{origin}: I'm not replying to \"{what}\".".format(
            origin=origin,
            what=what
        ))
        return

    Reply.delete().where(Reply.what == what).execute()

    client.message(target, "{origin}: Okay, I won't reply to {what} anymore.".format(
        origin=origin,
        what=what if is_regex(what) else "\"" + what + "\""
    ))


@service.hook("channel_message")
def do_reply(client, target, origin, message):
    replies = []

    for reply in Reply.select():
        if is_regex(reply.what):
            expr = reply.what[1:-1]
        else:
            expr = r"\b{}\b".format(re.escape(reply.what))
        if re.search(expr, message) is not None:
            replies.append(reply.reply)

    if not replies:
        return

    client.message(target, random.choice(replies))


@service.command(r"reply to (?P<what>.+?) with (?P<reply>.+)$", mention=True)
@requires_permission("reply")
def add_reply(client, target, origin, what, reply):
    """
    Add reply.

    ::

        $bot: reply to <what> with <reply>

    **Requires permission:** reply

    Add an automatic reply for whenever someone says `what`. `what` can be a
    regular expression delimited by ``/``, e.g. ``/^foo$/``.
    """

    if Reply.select().where(Reply.what == what).exists():
        client.message(target, "{origin}: I'm already replying to {what}.".format(
            origin=origin,
            what=what if is_regex(what) else "\"" + what + "\""
        ))
        return

    Reply.create(what=what, reply=reply).save()

    client.message(target, "{origin}: Okay, I'll reply to {what}.".format(
        origin=origin,
        what=what if is_regex(what) else "\"" + what + "\""
    ))


@service.command(r"what do you reply to\??$", mention=True)
@service.command(r"replies\??$", mention=True)
def list_replies(client, target, origin):
    """
    List replies.

    ::

        $bot: what do you reply to?
        $bot: replies?

    List all replies the bot has registered.
    """

    client.message(target, "{origin}: I reply to the following: {replies}".format(
        origin=origin,
        replies=", ".join(reply.what if is_regex(reply.what) else "\"" + reply.what + "\""
                          for reply in Reply.select().order_by(Reply.what))
    ))
