"""
Snapchat snap fetcher.

Allows users to send Snapchats to channels.
"""

import os
import glob
import humanize
import requests
import tempfile
import subprocess

from datetime import datetime, timedelta
from pysnap import Snapchat, MEDIA_VIDEO_NOAUDIO, MEDIA_VIDEO

from kochira import config
from kochira.service import Service, Config, background, HookContext

service = Service(__name__, __doc__)

@service.config
class Config(Config):
    username = config.Field(doc="The username to use when connecting.")
    password = config.Field(doc="The password to use when connecting.")
    imgur_clientid = config.Field(doc="Client ID for use with Imgur.")
    announce = config.Field(doc="Whether or not to announce. Set this on a per-channel basis.",
                            default=False)


GIF_FRAMERATE = 7
GIF_MAX_LENGTH = 360


def convert_to_gif(blob):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "video.mp4"), "wb") as f:
            f.write(blob)

        if subprocess.call(["ffmpeg",
                            "-i", os.path.join(d, "video.mp4"),
                            "-vf", "scale='iw*min({max_length}/iw,{max_length}/ih)':'ih*min({max_length}/iw,{max_length}/ih)'".format(max_length=GIF_MAX_LENGTH),
                            "-r", str(GIF_FRAMERATE),
                            os.path.join(d, "frames%03d.gif")]) != 0:
            return None

        if subprocess.call(["gifsicle",
                            "--delay={}".format(100 // GIF_FRAMERATE),
                            "--loop",
                            "-O",
                            "-o", os.path.join(d, "out.gif")] +
                            sorted(glob.glob(os.path.join(d, "frames[0-9][0-9][0-9].gif")))) != 0:
            return None

        with open(os.path.join(d, "out.gif"), "rb") as f:
            return f.read()


@service.setup
def make_snapchat(ctx):
    ctx.storage.snapchat = Snapchat()
    if not ctx.storage.snapchat.login(ctx.config.username, ctx.config.password) \
        .get("logged"):
        raise Exception("could not log into Snapchat")

    ctx.bot.scheduler.schedule_every(timedelta(seconds=30), poll_for_updates)


@service.task
@background
def poll_for_updates(ctx):
    has_snaps = False

    for snap in reversed(ctx.storage.snapchat.get_snaps()):
        has_snaps = True
        sender = snap["sender"]

        blob = ctx.storage.snapchat.get_blob(snap["id"])
        if blob is None:
            continue

        if snap["media_type"] in (MEDIA_VIDEO, MEDIA_VIDEO_NOAUDIO):
            blob = convert_to_gif(blob)

        if blob is not None:
            ulim = requests.post("https://api.imgur.com/3/upload.json",
                                 headers={"Authorization": "Client-ID " + ctx.config.imgur_clientid},
                                 data={"image": blob}).json()
            if ulim["status"] != 200:
                link = "(unavailable)"
            else:
                link = ulim["data"]["link"]
        else:
            link = ctx._("(could not convert video)")

        for client_name, client in ctx.bot.clients.items():
            for channel in client.channels:
                c_ctx = HookContext(service, ctx.bot, client, channel)

                if not c_ctx.config.announce:
                    continue

                c_ctx.message(
                    ctx._("New snap from {sender} ({dt})! {link}").format(
                        sender=sender,
                        link=link,
                        dt=humanize.naturaltime(datetime.fromtimestamp(snap["sent"] / 1000.0))
                    )
                )

        ctx.storage.snapchat.mark_viewed(snap["id"])

    if has_snaps:
        ctx.storage.snapchat._request("clear", {
            "username": ctx.storage.snapchat.username
        })
