import os
from pathlib import Path

import aiohttp

from config import YOUTUBE_COOKIES_URL


DOWNLOAD_DIR = Path("downloads")
COOKIE_FILE = DOWNLOAD_DIR / "cookies.txt"


async def refresh_youtube_cookies():
    """
    Private URL se cookies.txt download karke local file banata hai.
    """

    if not YOUTUBE_COOKIES_URL:
        return None

    temporary_file = DOWNLOAD_DIR / "cookies.txt.tmp"

    try:
        DOWNLOAD_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=60,
            connect=20,
            sock_read=40,
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            )
        }

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        ) as session:
            async with session.get(
                YOUTUBE_COOKIES_URL,
                allow_redirects=True,
            ) as response:
                if response.status != 200:
                    return None

                cookie_data = await response.read()

        if not cookie_data or len(cookie_data) < 20:
            return None

        cookie_text = cookie_data.decode(
            "utf-8",
            errors="ignore",
        )

        is_netscape_file = (
            "# Netscape HTTP Cookie File" in cookie_text
            or "# HTTP Cookie File" in cookie_text
            or ".youtube.com" in cookie_text
        )

        if not is_netscape_file:
            return None

        with open(temporary_file, "wb") as file:
            file.write(cookie_data)

        os.replace(
            temporary_file,
            COOKIE_FILE,
        )

        return str(COOKIE_FILE)

    except Exception:
        try:
            if temporary_file.exists():
                temporary_file.unlink()
        except Exception:
            pass

        return None


def get_cookie_file():
    if (
        COOKIE_FILE.exists()
        and COOKIE_FILE.stat().st_size > 20
    ):
        return str(COOKIE_FILE)

    return None


def yt_dlp_options(extra_options=None):
    """
    Har yt-dlp call ke liye common options.
    Cookie file available ho to automatically use hoti hai.
    """

    options = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
    }

    cookie_file = get_cookie_file()

    if cookie_file:
        options["cookiefile"] = cookie_file

    if extra_options:
        options.update(extra_options)

    return options
