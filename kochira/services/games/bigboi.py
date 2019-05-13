"""
Bigboi.

Descriptors for large lads.
"""

import random

from kochira.service import Service

service = Service(__name__, __doc__)

BIGS = (
    'big',
    'colossal',
    'dekai',
    'enormous',
    'gargantuan',
    'huge',
    'large',
    'mammoth',
    'ooki',
    'portly',
    'rotund',
    'sizable',
    'titanic',
    'tondemonai',
    'vast',
    'whopping',
)

BOIS_BY_FIRST_LETTER = {
    'b': ('boi',),
    'c': ('chap',),
    'd': ('dude',),
    'e': ('entity',),
    'g': ('guy',),
    'h': ('hito', 'human'),
    'l': ('lad',),
    'm': ('man',),
    'o': ('osananajimi', 'otoko'),
    'p': ('pal',),
    'r': ('rascal',),
    's': ('sonzai',),
    't': ('tomodachi',),
    'v': ('vassal',),
    'w': ('whippersnapper',),
}


@service.command(r"bigboi$", mention=True)
@service.command(r"!bigboi$")
def bigboi(ctx):
    """
    Describe a big boi.
    """
    big = random.choice(BIGS)
    boi = random.choice(BOIS_BY_FIRST_LETTER[big[0]])
    ctx.respond(ctx._("{} {}").format(big, boi))
