"""
Google web search.

Run queries on Google and return results.
"""

import requests

from kochira import config
from kochira.service import Service, background, Config, coroutine
from kochira.userdata import UserData

service = Service(__name__, __doc__)


@service.config
class Config(Config):
    api_key = config.Field(doc="Google API key.")
    cx = config.Field(doc="Custom search engine ID.")


@service.command(r"!g (?P<term>.+?)(?: (?P<num>\d+))?$")
@service.command(r"(?:search for|google) (?P<term>.+?)(?: \((?P<num>\d+)\))?\??$", mention=True)
@background
def search(ctx, term, num: int=None):
    """
    Google.

    Search for the given terms on Google. If a number is given, it will display
    that result.
    """

    r = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "key": ctx.config.api_key,
            "cx": ctx.config.cx,
            "q": term
        }
    ).json()

    results = r.get("items", [])

    if not results:
        ctx.respond(ctx._("Couldn't find anything matching \"{term}\".").format(term=term))
        return

    if num is None:
        num = 1

    num -= 1
    total = len(results)

    if num >= total or num < 0:
        ctx.respond(ctx._("Couldn't find anything matching \"{term}\".").format(term=term))
        return

    ctx.respond(ctx._("{title}: {url} ({num} of {total})").format(
        title=results[num]["title"],
        url=results[num]["link"],
        num=num + 1,
        total=total
    ))
