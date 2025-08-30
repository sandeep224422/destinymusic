import asyncio
import os
import re
import random
import aiohttp
import yt_dlp
from typing import Union
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from SONALI_MUSIC.utils.formatters import time_to_seconds

# === CONFIG ===
API_URL = "https://apikeyy-zeta.vercel.app/api"   # API key not required

def cookie_txt_file():
    cookie_dir = f"{os.getcwd()}/cookies"
    cookies_files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt")]
    cookie_file = os.path.join(cookie_dir, random.choice(cookies_files))
    return cookie_file


# ========== DOWNLOAD SONG ==========

async def download_song(link: str):
    """
    Try API download first, if fails -> fallback to cookies (yt-dlp).
    """
    video_id = link.split('v=')[-1].split('&')[0]
    download_folder = "downloads"
    os.makedirs(download_folder, exist_ok=True)

    # Check if already downloaded
    for ext in ["mp3", "m4a", "webm"]:
        file_path = f"{download_folder}/{video_id}.{ext}"
        if os.path.exists(file_path):
            return file_path

    # --- Step 1: Try API download ---
    song_url = f"{API_URL}/song/{video_id}"
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(song_url) as response:
                    if response.status != 200:
                        raise Exception(f"API request failed: {response.status}")
                    data = await response.json()
                    status = data.get("status", "").lower()
                    
                    if status == "downloading":
                        await asyncio.sleep(2)
                        continue
                    elif status == "error":
                        raise Exception(data.get("error") or "Unknown API error")
                    elif status == "done":
                        download_url = data.get("link")
                        file_format = data.get("format", "mp3").lower()
                        file_path = os.path.join(download_folder, f"{video_id}.{file_format}")

                        async with session.get(download_url) as file_response:
                            with open(file_path, 'wb') as f:
                                while True:
                                    chunk = await file_response.content.read(8192)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                        return file_path
                    else:
                        raise Exception(f"Unexpected API status: {status}")
    except Exception as e:
        print(f"[API FAILED] Falling back to cookies: {e}")

    # --- Step 2: Fallback to yt-dlp with cookies ---
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{download_folder}/%(id)s.%(ext)s",
            "geo_bypass": True,
            "nocheckcertificate": True,
            "cookiefile": cookie_txt_file(),
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            file_path = os.path.join(download_folder, f"{info['id']}.{info['ext']}")
            return file_path
    except Exception as e:
        print(f"[COOKIES FAILED] Could not download: {e}")
        return None


# ========== UTILS ==========

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


# ========== YOUTUBE API CLASS ==========

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset:length]

    async def details(self, link: str):
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def video(self, link: str):
        """
        Return direct video link.
        API first, fallback to yt-dlp.
        """
        try:
            song_file = await download_song(link)
            if song_file:
                return 1, song_file
        except Exception as e:
            print(f"[VIDEO API FAILED] {e}")

        # fallback
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--cookies", cookie_txt_file(),
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link, limit):
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --cookies {cookie_txt_file()} --playlist-end {limit} --skip-download {link}"
        )
        result = playlist.split("\n")
        return [r for r in result if r]

    async def track(self, link: str):
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            track_details = {
                "title": result["title"],
                "link": result["link"],
                "vidid": result["id"],
                "duration_min": result["duration"],
                "thumb": result["thumbnails"][0]["url"].split("?")[0],
            }
        return track_details, result["id"]

    async def download(self, link: str, video: bool = False, audio: bool = True):
        """
        Download using API first, fallback to yt-dlp + cookies.
        """
        try:
            file_path = await download_song(link)
            if file_path:
                return file_path, True
        except Exception as e:
            print(f"[DOWNLOAD API FAILED] {e}")

        # fallback with yt-dlp
        loop = asyncio.get_running_loop()
        def audio_dl():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        def video_dl():
            ydl_opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "cookiefile": cookie_txt_file(),
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        if video:
            return await loop.run_in_executor(None, video_dl), True
        else:
            return await loop.run_in_executor(None, audio_dl), True
