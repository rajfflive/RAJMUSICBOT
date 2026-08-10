import asyncio
import os
import re
from pathlib import Path
from typing import Union
from urllib.parse import urlsplit, urlunsplit

import aiofiles
import aiohttp
import yt_dlp
from dotenv import load_dotenv
from py_yt import Playlist, VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from SIMPLE_MUSIC.utils.formatters import time_to_seconds

from config import (
    API_KEY,
    API_URL,
    VIDEO_API_URL,
    YT_API_KEY,
    YTPROXY_URL,
)


load_dotenv()


DOWNLOAD_DIR = "downloads"
COOKIE_FILE = Path(DOWNLOAD_DIR) / "cookies.txt"
YOUTUBE_COOKIES_URL = os.getenv(
    "YOUTUBE_COOKIES_URL",
    "",
).strip()

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

CLIENT_SESSION = None
COOKIE_DOWNLOAD_TASK = None


def normalize_cookie_url(url: str) -> str:
    """
    Normal URL ko downloadable raw URL me convert karta hai.

    Supported examples:
        https://batbin.me/oswald
        https://www.batbin.me/oswald
        https://batbin.me/raw/oswald

    Batbin ke alawa kisi URL ko unchanged rakhta hai.
    """

    if not url:
        return ""

    try:
        parsed = urlsplit(url)
    except ValueError:
        return url

    hostname = (parsed.hostname or "").lower()

    if hostname not in {
        "batbin.me",
        "www.batbin.me",
        "p.batbin.me",
    }:
        return url

    paste_id = parsed.path.strip("/")

    if not paste_id:
        return url

    if paste_id.startswith("raw/"):
        raw_path = f"/{paste_id}"
    else:
        raw_path = f"/raw/{paste_id}"

    return urlunsplit(
        (
            "https",
            "batbin.me",
            raw_path,
            "",
            "",
        )
    )


YOUTUBE_COOKIES_URL = normalize_cookie_url(
    YOUTUBE_COOKIES_URL,
)


async def get_session():
    global CLIENT_SESSION

    if CLIENT_SESSION is None or CLIENT_SESSION.closed:
        CLIENT_SESSION = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=0),
        )

    return CLIENT_SESSION


async def prepare_youtube_cookies():
    """
    YOUTUBE_COOKIES_URL se Netscape-format cookies.txt download karta hai.

    Cookie URL ko environment variable/secret me rakhein.
    Cookies ko GitHub repository me commit na karein.
    """

    global COOKIE_DOWNLOAD_TASK

    if not YOUTUBE_COOKIES_URL:
        return None

    if (
        COOKIE_FILE.exists()
        and COOKIE_FILE.stat().st_size > 20
    ):
        return str(COOKIE_FILE)

    if COOKIE_DOWNLOAD_TASK is None:
        COOKIE_DOWNLOAD_TASK = asyncio.create_task(
            _download_youtube_cookies(),
        )

    try:
        return await COOKIE_DOWNLOAD_TASK
    except Exception:
        COOKIE_DOWNLOAD_TASK = None
        return None


async def _download_youtube_cookies():
    temporary_file = Path(
        f"{COOKIE_FILE}.tmp",
    )

    try:
        COOKIE_FILE.parent.mkdir(
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
            ),
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

        is_netscape_cookie_file = (
            "# Netscape HTTP Cookie File" in cookie_text
            or "# HTTP Cookie File" in cookie_text
            or ".youtube.com" in cookie_text
        )

        if not is_netscape_cookie_file:
            return None

        with open(temporary_file, "wb") as file:
            file.write(cookie_data)

        os.replace(
            temporary_file,
            COOKIE_FILE,
        )

        try:
            COOKIE_FILE.chmod(0o600)
        except OSError:
            pass

        return str(COOKIE_FILE)

    except Exception:
        return None

    finally:
        try:
            if temporary_file.exists():
                temporary_file.unlink()
        except OSError:
            pass


async def get_ytdl_options(extra_options=None):
    """
    Common yt-dlp options banata hai.
    Agar YOUTUBE_COOKIES_URL set hai to local cookie file automatically use hoti hai.
    """

    cookie_file = await prepare_youtube_cookies()

    options = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
    }

    if cookie_file:
        options["cookiefile"] = cookie_file

    if extra_options:
        options.update(extra_options)

    return options


async def _download_stream(
    url,
    file_path,
    headers=None,
):
    try:
        session = await get_session()

        timeout = aiohttp.ClientTimeout(
            total=None,
            sock_read=20,
        )

        async with session.get(
            url,
            headers=headers,
            timeout=timeout,
        ) as response:
            if response.status != 200:
                return None

            async with aiofiles.open(
                file_path,
                mode="wb",
            ) as file:
                async for chunk in response.content.iter_chunked(
                    2 * 1024 * 1024,
                ):
                    await file.write(chunk)

            if (
                os.path.exists(file_path)
                and os.path.getsize(file_path) > 1024
            ):
                return file_path

    except Exception:
        pass

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    return None


async def engine_shrutibots(
    vid_id: str,
    is_video: bool,
    file_path: str,
):
    try:
        session = await get_session()
        media_type = "video" if is_video else "audio"

        async with session.get(
            f"{API_URL}/download",
            params={
                "url": vid_id,
                "type": media_type,
            },
            timeout=7,
        ) as response:
            if response.status != 200:
                return None

            data = await response.json()
            token = data.get("download_token")

            if not token:
                return None

        stream_url = (
            f"{API_URL}/stream/{vid_id}"
            f"?type={media_type}&token={token}"
        )

        return await _download_stream(
            stream_url,
            file_path,
        )

    except Exception:
        return None


async def engine_xbit(
    vid_id: str,
    is_video: bool,
    file_path: str,
):
    if not YTPROXY_URL or not YT_API_KEY:
        return None

    try:
        session = await get_session()
        headers = {
            "x-api-key": YT_API_KEY,
        }

        async with session.get(
            f"{YTPROXY_URL}/info/{vid_id}",
            headers=headers,
            timeout=7,
        ) as response:
            if response.status != 200:
                return None

            data = await response.json()

        if data.get("status") != "success":
            return None

        stream_url = (
            data.get("video_url")
            if is_video
            else data.get("audio_url")
        )

        if not stream_url:
            return None

        return await _download_stream(
            stream_url,
            file_path,
            headers,
        )

    except Exception:
        return None


async def engine_nexgen(
    vid_id: str,
    is_video: bool,
    file_path: str,
):
    if not API_KEY:
        return None

    try:
        if is_video:
            url = (
                f"{VIDEO_API_URL}/video/"
                f"{vid_id}?api={API_KEY}"
            )
        else:
            url = (
                f"{API_URL}/song/"
                f"{vid_id}?api={API_KEY}"
            )

        session = await get_session()

        async with session.get(
            url,
            timeout=7,
        ) as response:
            if response.status != 200:
                return None

            data = await response.json()

        if (
            data.get("status", "").lower() != "done"
            or not data.get("link")
        ):
            return None

        return await _download_stream(
            data["link"],
            file_path,
        )

    except Exception:
        return None


def get_video_id(link: str):
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]

    return link.split("/")[-1].split("?")[0]


async def _core_download(
    link: str,
    is_video: bool,
):
    vid_id = get_video_id(link)
    extension = "mp4" if is_video else "mp3"

    final_path = os.path.join(
        DOWNLOAD_DIR,
        f"{vid_id}.{extension}",
    )

    if (
        os.path.exists(final_path)
        and os.path.getsize(final_path) > 1024
    ):
        return final_path

    tasks = [
        asyncio.create_task(
            engine_shrutibots(
                vid_id,
                is_video,
                f"{final_path}.shruti",
            ),
        ),
        asyncio.create_task(
            engine_xbit(
                vid_id,
                is_video,
                f"{final_path}.xbit",
            ),
        ),
        asyncio.create_task(
            engine_nexgen(
                vid_id,
                is_video,
                f"{final_path}.nexgen",
            ),
        ),
    ]

    winner = None

    for future in asyncio.as_completed(tasks):
        try:
            result = await future

            if result:
                winner = result

                for task in tasks:
                    if not task.done():
                        task.cancel()

                break

        except Exception:
            pass

    if winner and os.path.exists(winner):
        try:
            os.replace(winner, final_path)
            return final_path
        except OSError:
            return winner

    options = await get_ytdl_options(
        {
            "format": (
                "bestvideo[height<=480]"
                "[fps<=30][ext=mp4]+"
                "bestaudio[ext=m4a]/best"
                if is_video
                else "bestaudio/best"
            ),
            "outtmpl": final_path,
            "ignoreerrors": True,
        },
    )

    if not is_video:
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            },
        ]

    loop = asyncio.get_running_loop()

    def fallback_ytdl():
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([link])

    await loop.run_in_executor(
        None,
        fallback_ytdl,
    )

    if (
        os.path.exists(final_path)
        and os.path.getsize(final_path) > 1024
    ):
        return final_path

    # FFmpeg kabhi-kabhi final filename ko extension ke saath banata hai.
    if not is_video:
        generated_mp3 = os.path.splitext(final_path)[0] + ".mp3"

        if (
            os.path.exists(generated_mp3)
            and os.path.getsize(generated_mp3) > 1024
        ):
            return generated_mp3

    return None


async def download_song(link: str):
    return await _core_download(
        link,
        is_video=False,
    )


async def download_video(link: str):
    return await _core_download(
        link,
        is_video=True,
    )


class YouTubeAPI:
    def __init__(self):
        self.base = (
            "https://www.youtube.com/watch?v="
        )
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = (
            "https://www.youtube.com/oembed?url="
        )
        self.listbase = (
            "https://youtube.com/playlist?list="
        )
        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])",
        )

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        return bool(re.search(self.regex, link))

    async def url(
        self,
        message_1: Message,
    ):
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message,
            )

        for message in messages:
            for entity in message.entities or []:
                if entity.type == MessageEntityType.URL:
                    text = (
                        message.text
                        or message.caption
                        or ""
                    )

                    return text[
                        entity.offset: entity.offset
                        + entity.length
                    ]

            for entity in message.caption_entities or []:
                if (
                    entity.type
                    == MessageEntityType.TEXT_LINK
                ):
                    return entity.url

        return None

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1,
        )

        data = await results.next()
        result_list = data.get("result", [])

        if not result_list:
            return None, None, 0, None, None

        result = result_list[0]
        title = result["title"]
        duration_min = result["duration"]
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]

        duration_sec = (
            int(time_to_seconds(duration_min))
            if duration_min
            else 0
        )

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        )

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        return (
            await self.details(link, videoid)
        )[0]

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        return (
            await self.details(link, videoid)
        )[1]

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        return (
            await self.details(link, videoid)
        )[3]

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        try:
            result = await download_video(link)

            if result:
                return 1, result

            return 0, "Video download failed"

        except Exception as error:
            return 0, f"Video download error: {error}"

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.listbase + link

        if "&" in link:
            link = link.split("&")[0]

        try:
            data = await Playlist.get(link)
            videos = data.get("videos") or []

            return [
                item["id"]
                for item in videos[:limit]
                if item and item.get("id")
            ]

        except Exception:
            return []

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        results = VideosSearch(
            link,
            limit=1,
        )

        data = await results.next()
        result_list = data.get("result", [])

        if not result_list:
            return None

        result = result_list[0]

        return (
            {
                "title": result["title"],
                "link": result["link"],
                "vidid": result["id"],
                "duration_min": result["duration"],
                "thumb": result["thumbnails"][0]["url"].split("?")[0],
            },
            result["id"],
        )

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        options = await get_ytdl_options()

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(
                link,
                download=False,
            )

        formats = [
            {
                "format": item["format"],
                "filesize": item.get("filesize"),
                "format_id": item["format_id"],
                "ext": item["ext"],
                "format_note": item.get("format_note"),
                "yturl": link,
            }
            for item in info.get("formats", [])
            if "dash" not in str(
                item.get("format", ""),
            ).lower()
        ]

        return formats, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        if "&" in link:
            link = link.split("&")[0]

        data = await VideosSearch(
            link,
            limit=10,
        ).next()

        result = data.get("result", [])[query_type]

        return (
            result["title"],
            result["duration"],
            result["thumbnails"][0]["url"].split("?")[0],
            result["id"],
        )

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        is_video = bool(video)
        vid_id = get_video_id(link)

        duration_sec = 0
        is_live = False

        try:
            details = await self.details(link)
            duration_sec = details[2]
        except Exception:
            is_live = True

        if (
            is_live
            or duration_sec == 0
            or duration_sec > 3600
        ):
            try:
                session = await get_session()

                async with session.get(
                    f"{YTPROXY_URL}/info/{vid_id}",
                    headers={
                        "x-api-key": YT_API_KEY,
                    },
                    timeout=3,
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        stream_url = (
                            data.get("video_url")
                            if is_video
                            else data.get("audio_url")
                        )

                        if stream_url:
                            return stream_url, False

            except Exception:
                pass

            if is_video:
                media_format = (
                    "bestvideo[height<=480]"
                    "+bestaudio/best"
                )
            else:
                media_format = "bestaudio/best"

            options = await get_ytdl_options(
                {
                    "format": media_format,
                },
            )

            loop = asyncio.get_running_loop()

            def extract_direct_url():
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(
                        link,
                        download=False,
                    )

                return info.get("url")

            try:
                direct_url = await loop.run_in_executor(
                    None,
                    extract_direct_url,
                )

                if direct_url:
                    return direct_url, False

            except Exception:
                pass

        try:
            result = await _core_download(
                link,
                is_video,
            )

            if result:
                return result, True

            return None, False

        except Exception:
            return None, False
