#!/bin/bash
set -e

echo "================================================================="
echo "   THIRI // 24/7 AUTONOMOUS LIVE STREAM CONTAINER (RAILWAY)"
echo "================================================================="

STREAM_KEY="${YOUTUBE_STREAM_KEY:-$1}"
VIDEO_ID="${YOUTUBE_VIDEO_ID:-$2}"

if [ -z "$STREAM_KEY" ]; then
    echo "ERROR: YOUTUBE_STREAM_KEY environment variable is not set."
    echo "Please set YOUTUBE_STREAM_KEY in your Railway project settings."
    exit 1
fi

RTMP_URL="rtmp://a.rtmp.youtube.com/live2/$STREAM_KEY"
VISUAL="/app/thiri_stream_visual_1080p_v3.mp4"
FIFO="/tmp/thiri_live_audio.fifo"

# Clean up any stale FIFOs
rm -f "$FIFO"

# Detect font path
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if [ ! -f "$FONT" ]; then
    FONT="/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
fi
if [ ! -f "$FONT" ]; then
    FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
fi

echo "Visual:       $VISUAL"
echo "Target RTMP:  rtmp://a.rtmp.youtube.com/live2/****"
echo "Video ID:     ${VIDEO_ID:-[Not configured]}"
echo "Font file:    $FONT"
echo "================================================================="

# Initialize dynamic HUD files
echo "PROMPT: !mantra \"Peace within, clarity around\" !voice rachel" > /tmp/thiri_live_cmd.txt
echo "CHORDS: Dm9  ->  G13  ->  Cmaj9  ->  A7alt  |  TEMPO: 90 BPM (Lo-Fi)" > /tmp/thiri_live_chords.txt
echo "THIRI SANCTUARY: 432 Hz RESONANCE | VINYL CALM: ACTIVE | BOWL: READY" > /tmp/thiri_live_status.txt

# Start harmonic synthesis daemon
python3 /app/live_harmonic_generator.py &
GEN_PID=$!

# Start live chat listener if VIDEO_ID is provided
CHAT_PID=""
if [ -n "$VIDEO_ID" ]; then
    echo "Starting YouTube Live chat listener for video ID: $VIDEO_ID..."
    python3 /app/youtube_chat_listener.py "$VIDEO_ID" &
    CHAT_PID=$!
else
    echo "Notice: YOUTUBE_VIDEO_ID not provided. Live chat listener not started."
fi

# Wait for audio FIFO
while [ ! -p "$FIFO" ]; do
    sleep 0.1
done

trap "kill $GEN_PID $CHAT_PID 2>/dev/null; rm -f $FIFO" EXIT INT TERM

# Continuous broadcast loop
while true; do
    echo "⚡ [RTMP] Connecting to YouTube Live..."
    ffmpeg \
      -re \
      -stream_loop -1 \
      -i "$VISUAL" \
      -f s16le -ar 48000 -ac 2 \
      -i "$FIFO" \
      -vf "drawbox=x=950:y=860:w=920:h=170:color=0x0a0c1a@0.93:t=fill,drawbox=x=950:y=860:w=920:h=170:color=0xDEB938@0.9:t=2,drawbox=x=950:y=860:w=920:h=32:color=0x181a2e@0.95:t=fill,drawtext=fontfile='$FONT':text='THIRI  //  24/7 LO-FI SANCTUARY & LIVE AUDIENCE STEERING':x=970:y=868:fontsize=15:fontcolor=0xDEB938,drawtext=fontfile='$FONT':textfile='/tmp/thiri_live_cmd.txt':expansion=none:reload=1:x=970:y=904:fontsize=18:fontcolor=0x00D2FF,drawtext=fontfile='$FONT':textfile='/tmp/thiri_live_chords.txt':expansion=none:reload=1:x=970:y=936:fontsize=18:fontcolor=0xFFFFFF,drawtext=fontfile='$FONT':textfile='/tmp/thiri_live_status.txt':expansion=none:reload=1:x=970:y=968:fontsize=15:fontcolor=0x2ECC71" \
      -c:v libx264 -preset medium -tune animation -b:v 2600k -maxrate 2800k -bufsize 5200k -pix_fmt yuv420p -g 60 -keyint_min 60 -r 30 \
      -c:a aac -b:a 192k -ar 48000 \
      -f flv \
      -flvflags no_duration_filesize \
      "$RTMP_URL"

    EXIT_CODE=$?
    echo "⚠️ [RTMP] FFmpeg exited with code $EXIT_CODE. Reconnecting in 3 seconds..."
    sleep 3
done
