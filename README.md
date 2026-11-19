# Downly — public deployment starter

This project contains the Downly frontend, FastAPI backend, yt-dlp integration, FFmpeg support, and Docker deployment configuration.

## Deploy to Render (GitHub required)
1. Create a GitHub repository and upload all files in this folder.
2. Sign in to Render and choose **New → Blueprint**.
3. Connect the GitHub repository containing `render.yaml`.
4. Review the service settings and deploy.
5. When deployment completes, open the Render URL. Check `/health` for `{"status":"ok","service":"downly"}`.

Render's free instance may sleep when idle, has limited resources and ephemeral storage. Large media downloads can fail due to memory, CPU, timeout, disk, or provider limits. For a real public launch, use a paid instance, add a job queue, persistent object storage, download size/duration limits, rate limiting, abuse protection, monitoring, and a privacy/terms page.

## Local run with Docker
```bash
docker build -t downly .
docker run --rm -p 8000:8000 downly
```
Open http://localhost:8000

## Important
- This is deployment-ready starter code, not a guarantee that every website or every link can be downloaded.
- Platform extractors can break when websites change. Keep yt-dlp updated.
- Only download videos/audio you own or have permission to save. This service does not bypass DRM, paywalls, private accounts, or access controls.
- Before making it public, conduct a security review. Public URL fetchers are abuse targets; enforce strict egress controls and request limits.
- The starter stores download history in the visitor's browser only.
