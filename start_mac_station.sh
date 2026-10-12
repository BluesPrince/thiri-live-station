#!/bin/bash
# =============================================================================
# THIRI // 24/7 Autonomous Live Station (Option 1: Mac Local $0 Stack)
# Runs the Conductor Console, Harmonic Audio Generator, and Hardware-Accelerated
# FFmpeg RTMP Broadcaster directly on your local Mac.
# =============================================================================

set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

STREAM_KEY="${YOUTUBE_STREAM_KEY:-$1}"
VIDEO_ID="${YOUTUBE_VIDEO_ID:-$2}"

# Check for stream key in local env files if not set
if [ -z "$STREAM_KEY" ]; then
    for ENV_PATH in "$HERE/.env" "$HOME/.claude-os/.env.local" "$HOME/.env"; do
        if [ -f "$ENV_PATH" ]; then
            EXTRACTED=$(grep -E '^\s*YOUTUBE_STREAM_KEY\s*=' "$ENV_PATH" | cut -d '=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
            if [ -n "$EXTRACTED" ]; then
                STREAM_KEY="$EXTRACTED"
                break
            fi
        fi
    done
fi

echo "================================================================="
echo "   THIRI // 24/7 LIVE STREAM STATION (MAC LOCAL OPTION 1)"
echo "================================================================="

if [ -z "$STREAM_KEY" ]; then
    echo "⚠️  YOUTUBE_STREAM_KEY not provided as an argument or environment variable."
    echo "Usage: ./start_mac_station.sh <YOUR_YOUTUBE_STREAM_KEY> [OPTIONAL_VIDEO_ID]"
    echo ""
    echo "Note: You can still run the station locally in 'Audition / Preview' mode"
    echo "without streaming to YouTube. Starting local Conductor Console & Audio Generator..."
    MODE="preview"
else
    echo "Target RTMP: rtmp://a.rtmp.youtube.com/live2/****"
    MODE="broadcast"
fi

FIFO="/tmp/thiri_live_audio.fifo"
rm -f "$FIFO"

# Mac system font detection
FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
if [ ! -f "$FONT" ]; then
    FONT="/System/Library/Fonts/Helvetica.ttc"
fi

# Detect python virtualenv or default python3
PYTHON_BIN="python3"
VENV_CANDIDATE="/Users/bluesprincemedia/.gemini/antigravity-cli/scratch/claude-os/skills/thiri-magenta-series/.venv/bin/python"
if [ -f "$VENV_CANDIDATE" ]; then
    PYTHON_BIN="$VENV_CANDIDATE"
fi

echo "Python:       $PYTHON_BIN"
echo "Font:         $FONT"
echo "FIFO:         $FIFO"
echo "================================================================="

# Initialize HUD files
echo "BEAT #01: Midnight Jazz Djembe  |  STEERED BY: @BluesPrinceMedia" > /tmp/thiri_live_cmd.txt
echo "KEY: C Minor  |  TEMPO: 90 BPM  |  432Hz THETA (6Hz)" > /tmp/thiri_live_chords.txt
echo "THIRI GOVERNOR: 0.0% CLAMS | GUIDE TONES: 100% LOCKED | LIVE" > /tmp/thiri_live_status.txt

# 1. Start Conductor Console Web Server
echo "🚀 [1/3] Starting Conductor Console on http://localhost:8900..."
$PYTHON_BIN "$HERE/conductor_console.py" &
CONSOLE_PID=$!

# 2. Start Live Harmonic Generator
echo "🎵 [2/3] Starting Harmonic Generator Daemon..."
$PYTHON_BIN "$HERE/live_harmonic_generator.py" &
GEN_PID=$!

# 3. Start Live Chat Listener if Video ID provided
CHAT_PID=""
if [ -n "$VIDEO_ID" ]; then
    echo "💬 Starting YouTube Live chat listener for video ID: $VIDEO_ID..."
    $PYTHON_BIN "$HERE/youtube_chat_listener.py" "$VIDEO_ID" &
    CHAT_PID=$!
fi

# Cleanup on exit
trap "echo -e '\nStopping station...'; kill $CONSOLE_PID $GEN_PID $CHAT_PID 2>/dev/null; rm -f $FIFO; exit 0" EXIT INT TERM

# Wait for FIFO pipe
echo "Waiting for audio FIFO initialization..."
while [ ! -p "$FIFO" ]; do
    sleep 0.1
done

# Open Conductor in browser
sleep 1
if command -v open >/dev/null 2>&1; then
    open "http://localhost:8900/" || true
fi

if [ "$MODE" = "preview" ]; then
    echo "================================================================="
    echo "✅ Station running in local audition mode!"
    echo "👉 Open Conductor Console: http://localhost:8900/"
    echo "Press Ctrl+C to stop."
    echo "================================================================="
    # Keep process alive while listening to audio
    wait $GEN_PID
    exit 0
fi

# 4. Stream to YouTube Live via FFmpeg
echo "📺 [3/3] Broadcasting to YouTube Live..."
RTMP_URL="rtmp://a.rtmp.youtube.com/live2/$STREAM_KEY"
VISUAL="$HERE/thiri_stream_visual_1080p_v3.mp4"

# Check if videotoolbox (Apple Silicon Hardware Encoding) is supported
ENC_OPTS="-c:v h264_videotoolbox -b:v 2600k"
if ! ffmpeg -encoders 2>/dev/null | grep -q h264_videotoolbox; then
    ENC_OPTS="-c:v libx264 -preset ultrafast -tune animation -b:v 2600k"
fi

while true; do
    echo "⚡ Connecting RTMP stream to YouTube..."
    ffmpeg \
      -re \
      -stream_loop -1 \
      -i "$VISUAL" \
      -f s16le -ar 48000 -ac 2 \
      -i "$FIFO" \
      -vf "drawbox=x=950:y=860:w=920:h=170:color=0x0a0c1a@0.93:t=fill,drawbox=x=950:y=860:w=920:h=170:color=0xDEB938@0.9:t=2,drawbox=x=950:y=860:w=920:h=32:color=0x181a2e@0.95:t=fill,drawtext=fontfile='$FONT':text='THIRI  //  24/7 LO-FI SANCTUARY & LIVE AUDIENCE STEERING':x=970:y=868:fontsize=15:fontcolor=0xDEB938,drawtext=fontfile='$FONT':textfile='/tmp/thiri_live_cmd.txt':expansion=none:reload=1:x=970:y=904:fontsize=18:fontcolor=0x00D2FF,drawtext=fontfile='$FONT':textfile='/tmp/thiri_live_chords.txt':expansion=none:reload=1:x=970:y=936:fontsize=18:fontcolor=0xFFFFFF,drawtext=fontfile='$FONT':textfile='/tmp/thiri_live_status.txt':expansion=none:reload=1:x=970:y=968:fontsize=15:fontcolor=0x2ECC71" \
      $ENC_OPTS \
      -maxrate 2800k -bufsize 5200k -pix_fmt yuv420p -g 60 -keyint_min 60 -r 30 \
      -c:a aac -b:a 192k -ar 48000 \
      -f flv \
      -flvflags no_duration_filesize \
      "$RTMP_URL"

    EXIT_CODE=$?
    echo "⚠️ [RTMP] FFmpeg exited with code $EXIT_CODE. Reconnecting in 3 seconds..."
    sleep 3
done
