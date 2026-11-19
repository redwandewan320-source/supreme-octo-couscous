from pathlib import Path
from urllib.parse import urlparse
from ipaddress import ip_address
import socket
import shutil
import uuid
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
import yt_dlp

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
TEMP = BASE / "tmp"
TEMP.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("downly")

app = FastAPI(title="Downly API", version="1.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "facebook": ["facebook.com", "fb.watch"],
    "instagram": ["instagram.com"],
    "tiktok": ["tiktok.com"],
    "x": ["x.com", "twitter.com"],
    "pinterest": ["pinterest.com", "pin.it"],
    "reddit": ["reddit.com", "redd.it"],
    "vimeo": ["vimeo.com"],
    "dailymotion": ["dailymotion.com", "dai.ly"],
    "twitch": ["twitch.tv"],
    "soundcloud": ["soundcloud.com"],
    "other": []
}

class ExtractRequest(BaseModel):
    platform: str
    url: HttpUrl

class DownloadRequest(BaseModel):
    platform: str
    url: HttpUrl
    mode: str = "video"
    quality: str = "best"

def validate_url(platform: str, raw_url: str):
    if platform not in PLATFORMS:
        raise HTTPException(400, "Please choose a supported platform.")
    parsed = urlparse(raw_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in ("http", "https") or not host:
        raise HTTPException(400, "Only public HTTP/HTTPS URLs are accepted.")
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise HTTPException(400, "Local network URLs are not allowed.")
    try:
        resolved = socket.getaddrinfo(host, None)
        if not resolved:
            raise ValueError("No DNS results")
        for item in resolved:
            if not ip_address(item[4][0]).is_global:
                raise HTTPException(400, "Private or local network URLs are not allowed.")
    except socket.gaierror:
        raise HTTPException(400, "The URL host could not be resolved.")
    except ValueError:
        raise HTTPException(400, "The URL host could not be resolved.")

    allowed = PLATFORMS[platform]
    if allowed and not any(host == d or host.endswith("." + d) for d in allowed):
        raise HTTPException(400, "The URL does not match the selected platform.")
    return raw_url

def ydl_options():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 2,
        "max_filesize": 500 * 1024 * 1024,
    }

@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "downly"}

@app.post("/api/extract")
def extract(req: ExtractRequest):
    url = validate_url(req.platform, str(req.url))
    try:
        with yt_dlp.YoutubeDL({**ydl_options(), "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        formats, seen = [], set()
        for f in info.get("formats", []):
            if not f.get("url") or f.get("vcodec") == "none":
                continue
            height = f.get("height")
            label = f"{height}p" if height else f.get("format_note") or "Available"
            if label not in seen:
                seen.add(label)
                formats.append({"value": str(height or "best"), "label": label})
        formats.sort(key=lambda x: int(x["value"]) if x["value"].isdigit() else 99999, reverse=True)
        return {
            "title": info.get("title") or "Video",
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "formats": formats[:12] or [{"value": "best", "label": "Best available"}],
            "extractor": info.get("extractor_key")
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Extract failed")
        raise HTTPException(422, "Could not read this video. It may be private, unsupported, or unavailable.")

@app.post("/api/download")
def download(req: DownloadRequest):
    url = validate_url(req.platform, str(req.url))
    if req.mode not in ("video", "mp3", "thumbnail"):
        raise HTTPException(400, "Invalid download type.")
    job = uuid.uuid4().hex
    folder = TEMP / job
    folder.mkdir()
    output = str(folder / "%(title).70s.%(ext)s")
    opts = {**ydl_options(), "outtmpl": output, "restrictfilenames": True}

    if req.mode == "mp3":
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
        })
    elif req.mode == "thumbnail":
        opts.update({"skip_download": True, "writethumbnail": True})
    else:
        if req.quality == "best":
            opts["format"] = "bv*+ba/b"
        else:
            try:
                height = int(req.quality)
                if height not in (1080, 720, 480, 360):
                    raise ValueError()
            except ValueError:
                shutil.rmtree(folder, ignore_errors=True)
                raise HTTPException(400, "Unsupported quality.")
            opts["format"] = f"bv*[height<={height}]+ba/b[height<={height}]/b"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        outputs = [p for p in folder.iterdir() if p.is_file()]
        if not outputs:
            raise RuntimeError("No output file was created.")
        result = outputs[0]
        media = "image/jpeg" if req.mode == "thumbnail" else ("audio/mpeg" if req.mode == "mp3" else "application/octet-stream")
        # File is removed after the response has been sent.
        def cleanup():
            shutil.rmtree(folder, ignore_errors=True)
        return FileResponse(
            result,
            media_type=media,
            filename=result.name,
            background=BackgroundTask(cleanup)
        )
    except HTTPException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        log.exception("Download failed")
        raise HTTPException(422, "Download failed. The media may be unavailable or the platform may not support this format.")
