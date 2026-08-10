import asyncio
import os
import re
from typing import Union

import aiofiles
import aiohttp
import yt_dlp
from py_yt import Playlist, VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from SIMPLE_MUSIC.utils.formatters import time_to_seconds
from SIMPLE_MUSIC.utils.youtube_cookies import yt_dlp_options

from config import (
    API_KEY,
    API_URL,
    VIDEO_API_URL,
    YT_API_KEY,
    YTPROXY_URL,
)


DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

CLIENT_SESSION = None


async def get_session():
    global CLIENT_SESSION

    if CLIENT_SESSION is None or CLIENT_SESSION.closed:
        CLIENT_SESSION = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=0)
        )

    return CLIENT_SESSION


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
                    2 * 1024 * 1024
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
        except Exception:
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
            )
        ),
        asyncio.create_task(
            engine_xbit(
                vid_id,
                is_video,
                f"{final_path}.xbit",
            )
        ),
        asyncio.create_task(
            engine_nexgen(
                vid_id,
                is_video,
                f"{final_path}.nexgen",
            )
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
        except Exception:
            return winner

    loop = asyncio.get_running_loop()

    def fallback_ytdl():
        if is_video:
            media_format = (
                "bestvideo[height<=480]"
                "[fps<=30][ext=mp4]+"
                "bestaudio[ext=m4a]/best"
            )
        else:
            media_format = "bestaudio/best"

        options = yt_dlp_options(
            {
                "format": media_format,
                "outtmpl": final_path,
                "ignoreerrors": True,
            }
        )

        if not is_video:
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }
            ]

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
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
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
                message_1.reply_to_message
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
                        entity.offset : entity.offset
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

        options = yt_dlp_options()

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
                item.get("format", "")
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

            loop = asyncio.get_running_loop()

            def extract_direct_url():
                if is_video:
                    media_format = (
                        "bestvideo[height<=480]"
                        "+bestaudio/best"
                    )
                else:
                    media_format = "bestaudio/best"

                options = yt_dlp_options(
                    {
                        "format": media_format,
                    }
                )

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

        try: **…**

_This response is too long to display in full._
