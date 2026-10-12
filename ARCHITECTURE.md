# 24/7 Agentic Radio Station: Technical Architecture

## Overview
The 24/7 Autonomous Agentic Radio Station architecture isolates three asynchronous loops to guarantee continuous broadcast stability with zero laptop load and sub-second chat responsiveness.

```mermaid
flowchart TD
    subgraph LoopB ["Loop B: Audience Chat Daemon (pytchat)"]
        Chat[YouTube Live Chat Stream] -->|Zero API Quota Scrape| Parser[Command Parser: !tempo, !key, !affirmation]
        Parser -->|Atomic JSON Write| StateFile[stream_state.json]
    end

    subgraph LoopA ["Loop A: Audio DSP Synthesis (Python / NumPy)"]
        StateFile -->|Read at 4-Bar Boundaries| DSPCore[DSP Harmonic Engine]
        DSPCore --> KeysL[Rhodes Voice: Left Pan -0.25]
        DSPCore --> KeysR[Felt Piano: Detuned Reverb Right Pan +0.25]
        DSPCore --> Bass[Sine Sub Bass: 8% 2nd Harmonic]
        DSPCore --> Noise[Vinyl Bed & 432 Hz Singing Bowls]
        DSPCore --> Beat[Splice Drum Loop: 90 BPM Locked]
        TTS[ElevenLabs Voice Engine] -->|Sidechain Ducking -12 dB| Mixer[Dynamic Audio Mixer]
        KeysL --> Mixer
        KeysR --> Mixer
        Bass --> Mixer
        Noise --> Mixer
        Beat --> Mixer
        Mixer -->|Raw PCM / Named Pipe| AudioFIFO[audio.fifo]
    end

    subgraph LoopC ["Loop C: Video Multiplexing & RTMP Egress (FFmpeg)"]
        StateFile -->|Frame State| HUD[HUD Visual Generator: 1280x720]
        HUD -->|Telemetry Overlay| FFmpeg[FFmpeg Transcoder]
        AudioFIFO --> FFmpeg
        BG[Background Video Loop: thiri_stream_visual] --> FFmpeg
        FFmpeg -->|RTMP Ingest: 2500 kbps, -g 60| YouTube[YouTube Live Ingest Server]
    end
```

## Core Design Principles

1. **Loop Isolation & Zero Dropouts**:
   Audio DSP generation runs strictly ahead of time in 4-bar chunks (~10.667 seconds at 90 BPM). Chat ingestion never interrupts an active chunk; changes take effect cleanly at musical turnaround points.

2. **2-Second Keyframe Synchronization**:
   FFmpeg enforces strict 2.0-second GOP (`-g 60` at 30 fps) to maintain seamless ingestion with YouTube Live ingest servers without buffering.

3. **Atomic File-Based State Machine**:
   `stream_state.json` serves as the thread-safe communication bus between the Python chat listener, the DSP harmonic engine, and the visual overlay renderer.
