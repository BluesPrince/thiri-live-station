# THIRI // 24/7 Autonomous Generative Radio Station (Railway Cloud Deployment)

**Arranged & Produced by**: Blues Prince Media  
**Sound Engine**: Serum 2 & Splice Instruments | **AI Core**: Google Magenta  
**Harmonic Governor**: THIRI Helix Drop-2 Voice Leading  

This repository runs an autonomous 24/7 promptable generative music livestream on YouTube Live with zero local hardware dependency.

---

## Architecture

1. **Audio Synthesis Daemon (`live_harmonic_generator.py`)**:
   Continuously generates 4-bar halftime dubstep and jazz chord progressions in real time at 140 BPM, piping raw 48 kHz stereo PCM into `/tmp/thiri_live_audio.fifo`.
2. **Chat Listener Daemon (`youtube_chat_listener.py`)**:
   Monitors YouTube Live chat in real time, parsing viewer prompts (`!prog`, `!key`, `!chaos`, `!drums`, `!drop`, `!breakdown`) and updating `stream_state.json`.
3. **Video Muxer (`ffmpeg`)**:
   Streams the 1080p landscape visualizer loop (`thiri_stream_visual_1080p_v3.mp4`) with an active on-screen audience HUD (`drawbox` + `drawtext`) directly into YouTube RTMP ingest with strict 2-second keyframes (`-g 60 -r 30`).

---

## Deployment to Railway

### 1. Push to GitHub
```bash
cd /Users/bluesprincemedia/code/thiri-live-station
git init
git add .
git commit -m "THIRI 24/7 live station container for Railway"
gh repo create thiri-live-station --public --source=. --push
```

### 2. Connect to Railway
1. Open [railway.com](https://railway.com) (or [railway.app](https://railway.app)).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select **`BluesPrince/thiri-live-station`**.

### 3. Add Environment Variables in Railway
Under **Variables** in your Railway service settings, add:
* `YOUTUBE_STREAM_KEY`: `z2er-wjtj-x9s3-cvay-ajq7`
* `YOUTUBE_VIDEO_ID`: `jfuyBE5ohFA`

Railway will automatically build the Docker image and stream continuously 24/7. Once deployed, you can close your computer and the YouTube Live station will run permanently.
