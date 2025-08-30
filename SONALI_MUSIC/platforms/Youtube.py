import asyncio
import os
import re
import json
import random
import aiohttp
import yt_dlp
from typing import Union
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from SONALI_MUSIC.utils.database import is_on_off
from SONALI_MUSIC.utils.formatters import time_to_seconds

# === CONFIG ===
API_URL = "https://apikeyy-zeta.vercel.app/api"
API_KEY = "your_api_key_here"   # Agar zarurat ho

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
    song_url = f"{API_URL}/song/{video_id}?api={API_KEY}"
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
