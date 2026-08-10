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
import requests
from SIMPLE_MUSIC import app
from pyrogram import Client, filters

JOKE_API_ENDPOINT = 'https://hindi-jokes-api.onrender.com/jokes?api_key=1a6d440e3f5971eecebceee818c2'

@app.on_message(filters.command("hjoke"))
async def joke(_, message):
    response = requests.get(JOKE_API_ENDPOINT)
    r = response.json()
    joke_text = r['jokeContent']
    await message.reply_text(joke_text)
