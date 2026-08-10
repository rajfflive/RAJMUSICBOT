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
from pyrogram import Client, filters
from pyrogram.types import Message
from SIMPLE_MUSIC import app
from config import OWNER_ID
import aiohttp
import re

# Small caps helper function for stylish font
def to_small_caps(text):
    mapping = {
        "a":"ᴀ","b":"ʙ","c":"ᴄ","d":"ᴅ","e":"ᴇ","f":"ꜰ","g":"ɢ","h":"ʜ","i":"ɪ","j":"ᴊ",
        "k":"ᴋ","l":"ʟ","m":"ᴍ","n":"ɴ","o":"ᴏ","p":"ᴘ","q":"ǫ","r":"ʀ","s":"s","t":"ᴛ",
        "u":"ᴜ","v":"ᴠ","w":"ᴡ","x":"x","y":"ʏ","z":"ᴢ",
        "A":"ᴀ","B":"ʙ","C":"ᴄ","D":"ᴅ","E":"ᴇ","F":"ꜰ","G":"ɢ","H":"ʜ","I":"ɪ","J":"ᴊ",
        "K":"ᴋ","L":"ʟ","M":"ᴍ","N":"ɴ","O":"ᴏ","P":"ᴘ","Q":"ǫ","R":"ʀ","S":"s","T":"ᴛ",
        "U":"ᴜ","V":"ᴠ","W":"ᴡ","X":"x","Y":"ʏ","Z":"ᴢ"
    }
    return "".join(mapping.get(c, c) for c in text)

# vc on
@app.on_message(filters.video_chat_started)
async def brah(_, msg):
       await msg.reply("👉 **ᴠᴏɪᴄᴇ ᴄʜᴀᴛ sᴛᴀʀᴛᴇᴅ**😍")

# vc off
@app.on_message(filters.video_chat_ended)
async def brah2(_, msg):
       await msg.reply("👉**ᴠᴄ ᴄʜᴀᴛ ᴇɴᴅᴇᴅ**😆")

# invite members on vc (EDITED AS PER IMAGE 23218.jpg)
@app.on_message(filters.video_chat_members_invited)
async def brah3(app: app, message: Message):
           # Invite karne wale ka naam aur mention link
           inviter_name = to_small_caps(message.from_user.first_name)
           inviter_mention = message.from_user.mention(inviter_name)
           
           invited_users_list = []
           for user in message.video_chat_members_invited.users:
               try:
                   # Jinko invite kiya gaya hai unke naam aur links
                   user_name = to_small_caps(user.first_name)
                   invited_users_list.append(f"[{user_name}](tg://user?id={user.id})")
               except Exception:
                   pass
           
           if not invited_users_list:
               return

           # Agar ek se zyada log hain toh comma se alag honge
           invited_members = ", ".join(invited_users_list)
           
           # 📝 Image 23218.jpg ke mutabik naya layout text
           final_text = f"🎤 {invited_members} **ɢᴏᴛ ᴀɴ ɪɴᴠɪᴛᴇ ғʀᴏᴍ** {inviter_mention} 💌"
           
           try:
               await message.reply(final_text)
           except Exception:
               pass


####

@app.on_message(filters.command("math"))
async def calculate_math(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Usage:\n`/math 2+2`",
            quote=True
        )

    expression = message.text.split(None, 1)[1]

    try:
        result = eval(expression)
        response = f"✅ **Result:** `{result}`"
    except Exception:
        response = "❌ **Invalid expression**"

    await message.reply_text(response, quote=True)

###
@app.on_message(filters.command("leavegroup") & filters.user(OWNER_ID))
async def bot_leave(_, message):
    chat_id = message.chat.id
    text = f"sᴜᴄᴄᴇssғᴜʟʟʏ   ʟᴇғᴛ  !!."
    await message.reply_text(text)
    await app.leave_chat(chat_id=chat_id, delete=True)


####

@app.on_message(filters.command(["spg"], ["/", "!", "."]))
async def search(event):
    msg = await event.respond("Searching...")
    async with aiohttp.ClientSession() as session:
        start = 1
        async with session.get(f"https://content-customsearch.googleapis.com/customsearch/v1?cx=ec8db9e1f9e41e65e&q={event.text.split()[1]}&key=AIzaSyAa8yy0GdcGPHdtD083HiGGx_S0vMPScDM&start={start}", headers={"x-referer": "https://explorer.apis.google.com"}) as r:
            response = await r.json()
            result = ""

            if not response.get("items"):
                return await msg.edit("No results found!")
            for item in response["items"]:
                title = item["title"]
                link = item["link"]
                if "/s" in item["link"]:
                    link = item["link"].replace("/s", "")
                elif re.search(r'\/\d', item["link"]):
                    link = re.sub(r'\/\d', "", item["link"])
                if "?" in link:
                    link = link.split("?")[0]
                if link in result:
                    # remove duplicates
                    continue
                result += f"{title}\n{link}\n\n"
            prev_and_next_btns = [Button.inline("▶️Next▶️", data=f"next {start+10} {event.text.split()[1]}")]
            await msg.edit(result, link_preview=False, buttons=prev_and_next_btns)
            await session.close()
