"""
Unicode character database.

Identify unicode characters.
"""

import unicodedata

from kochira.service import Service

service = Service(__name__, __doc__)


@service.command(r"!u (?P<character>.)", re_flags=0)
def query(ctx, character):
    """
    Query.

    Find information about a Unicode character.
    """

    try:
        name = unicodedata.name(character)
    except ValueError:
        ctx.respond(ctx._("I don't know what that character is."))
        return

    category = unicodedata.category(character)

    ctx.respond(ctx._("{character} (U+{ord:04X}) {name} (Category: {category})").format(
        character=character,
        ord=ord(character),
        name=name,
        category=category
    ))


@service.command(r"!u [Uu]\+(?P<escape>[0-9a-fA-F]{1,6})", re_flags=0)
def query_escape(ctx, escape):
    """
    Query escape.

    Find information about a Unicode character escape.
    """

    try:
        character = chr(int(escape, 16))
    except ValueError:
        ctx.respond(ctx._("I don't know what that escape is."))
        return

    try:
        name = unicodedata.name(character)
    except ValueError:
        ctx.respond(ctx._("I don't know what that character is."))
        return

    category = unicodedata.category(character)

    ctx.respond(ctx._("{character} (U+{ord:04X}) {name} (Category: {category})").format(
        character=character,
        ord=ord(character),
        name=name,
        category=category
    ))


@service.command(r"!U (?P<name>.+)", re_flags=0)
def lookup(ctx, name):
    """
    Lookup.

    Lookup a Unicode character by name.
    """

    name = name.upper()

    try:
        character = unicodedata.lookup(name)
    except KeyError:
        ctx.respond(ctx._("I don't know what that character is."))
        return

    category = unicodedata.category(character)

    ctx.respond(ctx._("{character} (U+{ord:04X}) {name} (Category: {category})").format(
        character=character,
        ord=ord(character),
        name=name,
        category=category
    ))
