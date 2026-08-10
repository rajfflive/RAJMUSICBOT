# 🔹 Customized & Branded by: Rajbots
# 🔗 Project: https://github.com/rajfflive/RAJMUSICBOT
# -----------------------------------------------
# 🔸 RAJ MUSIC BOT
# 🔹 Developed and maintained by Rajbots
# -----------------------------------------------

import asyncio
import importlib

from pyrogram import idle
from pyrogram.types import BotCommand
from pytgcalls.exceptions import NoActiveGroupCall

import config
from config import BANNED_USERS
from SIMPLE_MUSIC import LOGGER, app, userbot
from SIMPLE_MUSIC.core.call import SIMPLE
from SIMPLE_MUSIC.misc import sudo
from SIMPLE_MUSIC.plugins import ALL_MODULES
from SIMPLE_MUSIC.utils.database import (
    get_banned_users,
    get_gbanned,
)


COMMANDS = [
    BotCommand(
        "start",
        "Start the bot",
    ),
    BotCommand(
        "help",
        "Get help and commands",
    ),
    BotCommand(
        "ping",
        "Check bot status",
    ),
    BotCommand(
        "play",
        "Play music in voice chat",
    ),
]


# These modules contain the music and voice-chat handlers.
# They are outside the plugins folder, so they must be loaded separately.
PLAY_MODULES = [
    "play.play",
    "play.channel",
    "play.live",
    "play.playmode",
]


async def setup_bot_commands():
    try:
        await app.set_bot_commands(COMMANDS)
        LOGGER("SIMPLE_MUSIC").info(
            "Bot commands set successfully!"
        )
    except Exception as error:
        LOGGER("SIMPLE_MUSIC").error(
            f"Failed to set bot commands: {error}"
        )


def load_bot_modules():
    """
    Load all normal plugins and all music/voice-chat modules.
    """

    # Load modules from SIMPLE_MUSIC/plugins/
    for module in ALL_MODULES:
        module_name = f"SIMPLE_MUSIC.plugins{module}"
        importlib.import_module(module_name)

    # Load modules from SIMPLE_MUSIC/play/
    for module in PLAY_MODULES:
        module_name = f"SIMPLE_MUSIC.{module}"
        importlib.import_module(module_name)

    LOGGER("SIMPLE_MUSIC.plugins").info(
        "All bot and music modules loaded successfully."
    )


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error(
            "STRING_SESSION is not configured. "
            "Please add a Pyrogram session string."
        )
        return

    await sudo()

    try:
        global_banned_users = await get_gbanned()

        for user_id in global_banned_users:
            BANNED_USERS.add(user_id)

        banned_users = await get_banned_users()

        for user_id in banned_users:
            BANNED_USERS.add(user_id)

    except Exception as error:
        LOGGER("SIMPLE_MUSIC").error(
            f"Could not load banned users: {error}"
        )

    await app.start()
    await setup_bot_commands()

    # Important:
    # This must run before the bot starts accepting commands.
    load_bot_modules()

    LOGGER("SIMPLE_MUSIC").info(
        "Music Bot started as RAJBOTSBOT."
    )

    await userbot.start()
    await SIMPLE.start()

    try:
        await SIMPLE.stream_call(
            "https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4"
        )

    except NoActiveGroupCall:
        LOGGER("SIMPLE_MUSIC").error(
            "Please start a voice chat in your log group/channel "
            "before starting the music bot."
        )
        await app.stop()
        await userbot.stop()
        return

    except Exception as error:
        LOGGER("SIMPLE_MUSIC").error(
            f"Initial stream check failed: {error}"
        )

    await SIMPLE.decorators()

    LOGGER("SIMPLE_MUSIC").info(
        "RAJ MUSIC BOT is fully started and ready."
    )

    await idle()

    await app.stop()
    await userbot.stop()

    LOGGER("SIMPLE_MUSIC").info(
        "RAJ MUSIC BOT stopped."
    )


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
