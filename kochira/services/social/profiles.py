"""
Personal profiles.

This service allows the bot to keep track of people's profiles.

Commands
========

Remember Profile
----------------

::

    $bot: i am <text>

Associate the given profile text with the user.

Forget Profile
--------------

::

    $bot: forget about me

Remove the given profile text from the user.

Get Profile
-----------

::

    $bot: who am i
    $bot: who is <who>

Retrieve profile text for a user.
"""

from peewee import CharField, TextField

from kochira.db import Model

from kochira.service import Service

service = Service(__name__, __doc__)


class Profile(Model):
    who = CharField(255)
    network = CharField(255)
    text = TextField()

    class Meta:
        indexes = (
            (("who", "network"), True),
        )


@service.setup
def initialize_model(bot):
    Profile.create_table(True)


@service.command(r"forget(?: about)? me$", mention=True)
def forget_profile(client, target, origin):
    if Profile.delete().where(Profile.network == client.network,
                              Profile.who == origin).execute():
        client.message(target, "{origin}: Okay, I won't remember you anymore.".format(
            origin=origin
        ))
    else:
        client.message(target, "{origin}: I don't know who you are.".format(
            origin=origin
        ))


@service.command(r"[Ii](?: a|')m (?P<text>.+)$", mention=True)
def remember_profile(client, target, origin, text):
    try:
        profile = Profile.get(Profile.network == client.network,
                              Profile.who == origin)
    except Profile.DoesNotExist:
        profile = Profile.create(network=client.network, who=origin,
                                 text=text)

    profile.text = text
    profile.save()

    client.message(target, "{origin}: Okay, I'll remember you.".format(
        origin=origin
    ))


@service.command(r"who am [Ii]\??$", mention=True)
@service.command(r"who(?: is|'s| the .* is) (?P<who>\S+)\??$", mention=True)
def get_profile(client, target, origin, who=None):
    if who is None:
        who = origin

    try:
        profile = Profile.get(Profile.network == client.network,
                              Profile.who == who)
    except Profile.DoesNotExist:
        client.message(target, "{origin}: {who} hasn't told me who they are yet.".format(
            origin=origin,
            who=who
        ))
    else:
        client.message(target, "{origin}: {who} is {text}".format(
        origin=origin,
        who=profile.who,
        text=profile.text
    ))
