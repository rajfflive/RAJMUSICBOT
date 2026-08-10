# 🔹 Customized & Branded by: Rajbots
# 🔗 Project: https://github.com/rajfflive/RAJMUSICBOT/new/main
# -----------------------------------------------
# 🔸 SIMPLE MUSIC Project
# 🔹 Developed & Maintained by: Rajbots (https://github.com/rajfflive/RAJMUSICBOT/new/main)
# 📅 Copyright © 2026 – All Rights Reserved
#
# 📖 License:
# This source code is open for educational and non-commercial use ONLY.
# You are required to retain this credit in all copies or substantial portions of this file.
# Commercial use, redistribution, or removal of this notice is strictly prohibited
# without prior written permission from the author.
#
# ❤️ Made with dedication and love by Rajbots
# -----------------------------------------------
import random
import asyncio
import config
from SIMPLE_MUSIC import app
from pyrogram import Client, filters, enums
from pyrogram.errors import RPCError
from pyrogram.types import ChatMemberUpdated
from os import environ
from typing import Union, Optional

# --------------------------------------------------------------------------------- #
# Note: Saare bade text, buttons aur auto-delete handler ko hata diya gaya hai.
# --------------------------------------------------------------------------------- #

@app.on_chat_member_updated(filters.group, group=20)
async def member_has_left(client: app, member: ChatMemberUpdated):

    if (
        not member.new_chat_member
        and member.old_chat_member.status not in {
            "banned", "left", "restricted"
        }
        and member.old_chat_member
    ):
        pass
    else:
        return

    user = (
        member.old_chat_member.user
        if member.old_chat_member
        else member.from_user
    )

    try:
        # ✨ Ekdum short text format jo sirf left karne wale ka naam dikhayega:
        text = f"**{user.first_name} left the group... 🥺💔**"

        # Direct chhota text message send hoga aur yeh kabhi auto-delete nahi hoga
        await client.send_message(
            chat_id=member.chat.id,
            text=text
        )
        
    except RPCError as e:
        print(e)
        return
