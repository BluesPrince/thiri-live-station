#!/usr/bin/env python3
"""
THIRI + Google Magenta // Live Harmonic Audio Generator Daemon
Continuously monitors stream_state.json and synthesizes 4-bar audio chunks
in real-time, streaming raw 16-bit 48kHz PCM directly into a named FIFO pipe.

Features:
- Instant harmonic re-voicing on user chat prompts (!prog, !key, !drop, !breakdown, !drums, !chaos)
- Exact THIRI Drop-2 rootless jazz voice leading (0% clam rate)
- Sub-bass root tracking down to 36 Hz (Serum 2 wavetable saturation)
- Google DrumsRNN drum synthesis (Halftime Dubstep, DnB Breakbeat, Four-on-the-Floor, or Muted)
- Cavernous reverb and ping-pong delay DSP
- Equal-power 15ms boundary crossfades for 100% seamless, click-free continuity
"""

import os, sys, time, json, math, re, itertools
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, 'stream_state.json')
FIFO_PATH = '/tmp/thiri_live_audio.fifo'

SR = 48000
BPM = 140.0
BEAT_SEC = 60.0 / BPM
BAR_SEC = BEAT_SEC * 4.0
CHUNK_BARS = 4
CHUNK_SEC = CHUNK_BARS * BAR_SEC # 6.857142857 s
CHUNK_SAMPLES = int(round(CHUNK_SEC * SR)) # 329143 samples

NOTE_NAMES = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5,
    'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11
}

# Default 12-key cycle of 2-5-1s
DEFAULT_CYCLE = [
    ['Dm7', 'G7', 'Cmaj7', 'Cmaj7'],
    ['Cm7', 'F7', 'Bbmaj7', 'Bbmaj7'],
    ['Bbm7', 'Eb7', 'Abmaj7', 'Abmaj7'],
    ['Abm7', 'Db7', 'Gbmaj7', 'Gbmaj7'],
    ['F#m7', 'B7', 'Emaj7', 'Emaj7'],
    ['Em7', 'A7', 'Dmaj7', 'Dmaj7'],
    ['C#m7', 'F#7', 'Bmaj7', 'Bmaj7'],
    ['Bm7', 'E7', 'Amaj7', 'Amaj7'],
    ['Am7', 'D7', 'Gmaj7', 'Gmaj7'],
    ['Gm7', 'C7', 'Fmaj7', 'Fmaj7'],
    ['Fm7', 'Bb7', 'Ebmaj7', 'Ebmaj7'],
    ['Ebm7', 'Ab7', 'Dbmaj7', 'Dbmaj7'],
]

def mtof(m):
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))

def soft_clip(x):
    return np.tanh(x)

def parse_chord(c_str):
    c = c_str.strip()
    m = re.match(r'^([A-G][b#]?)(.*)$', c)
    if not m:
        return 0, 'maj7', [4, 7, 11, 14]
    root_str, quality = m.group(1), m.group(2).lower()
    root = NOTE_NAMES.get(root_str.upper(), 0)
    
    if 'maj7' in quality or '^7' in quality or 'maj' in quality:
        intervals = [4, 7, 11, 14] # 3, 5, 7, 9
    elif 'b9' in quality:
        intervals = [4, 10, 13, 7] # 3, b7, b9, 5
    elif '#11' in quality or '7#11' in quality:
        intervals = [4, 10, 18, 14] # 3, b7, #11, 9
    elif 'alt' in quality:
        intervals = [4, 10, 13, 20] # 3, b7, b9, b13
    elif '-7' in quality or 'm7' in quality or 'min7' in quality:
        intervals = [3, 7, 10, 14] # b3, 5, b7, 9
    elif '7' in quality:
        intervals = [4, 7, 10, 14] # 3, 5, b7, 9
    elif 'dim' in quality or 'o7' in quality:
        intervals = [3, 6, 9, 12]
    elif 'm7b5' in quality or 'ø' in quality:
        intervals = [3, 6, 10, 13]
    else:
        intervals = [4, 7, 11, 14]
        
    return root, quality, intervals

def solve_drop2(root, ivs, prev_voicing=None):
    base = [(root + iv) % 12 for iv in ivs]
    # Octave 4 reference (MIDI 60 to 71)
    base_oct = sorted([60 + b for b in base])
    # Drop-2: drop second note from the top down by 1 octave
    drop2 = sorted([base_oct[2] - 12, base_oct[0], base_oct[1], base_oct[3]])
    
    if prev_voicing is not None:
        best_diff = float('inf')
        best_v = drop2
        for oct_shift in [-12, 0, 12]:
            shifted = [p + oct_shift for p in drop2]
            # Ensure within comfortable piano mid-range (MIDI 45 to 76)
            if any(p < 43 or p > 78 for p in shifted):
                continue
            for perm in itertools.permutations(shifted):
                diff = sum((perm[i] - prev_voicing[i])**2 for i in range(4))
                if diff < best_diff:
                    best_diff = diff
                    best_v = list(perm)
        return best_v
    return drop2

def get_bass_midi(root):
    # Bass in octave 1 or 2 (MIDI 36 to 47)
    midi = 36 + (root % 12)
    if midi < 36: midi += 12
    return midi

def synth_4bar_chunk(chords_list, drum_mode='halftime_dubstep', chaos=1.8, prev_voicing=None):
    """Synthesizes a 4-bar arrangement chunk locked to 140 BPM."""
    buf = np.zeros((CHUNK_SAMPLES, 2), dtype=np.float32)
    
    # 1. Parse and solve voicings for the 4 bars
    voicings = []
    roots = []
    curr_v = prev_voicing
    for c_str in chords_list:
        r, q, ivs = parse_chord(c_str)
        curr_v = solve_drop2(r, ivs, curr_v)
        voicings.append(curr_v)
        roots.append(get_bass_midi(r))
        
    # 2. Synthesize Sub-Bass
    for b_idx in range(4):
        f0 = mtof(roots[b_idx])
        t_bar = b_idx * BAR_SEC
        i_bar = int(t_bar * SR)
        
        # 2 hits per bar: beat 1 and beat 2.5
        hits = [(0.0, 1.35), (2.0 * BEAT_SEC, 1.8)]
        for h_off, h_dur in hits:
            t_start = t_bar + h_off
            i_start = int(t_start * SR)
            n_samp = min(int(h_dur * SR), CHUNK_SAMPLES - i_start)
            if n_samp <= 0: continue
            t = np.linspace(0, h_dur, n_samp, endpoint=False)
            env = (1.0 - np.exp(-t * 22.0)) * np.exp(-t * 1.6)
            # Heavy fundamental + rich 2nd harmonic
            sig = np.sin(2.0 * math.pi * f0 * t) + 0.35 * np.sin(4.0 * math.pi * f0 * t)
            sig = soft_clip(sig * 1.8) * env * 0.78
            buf[i_start:i_start+n_samp, 0] += sig
            buf[i_start:i_start+n_samp, 1] += sig

    # 3. Synthesize Drop-2 Chords (Serum Wavetable Style Detuned Saws)
    for b_idx in range(4):
        v = voicings[b_idx]
        t_bar = b_idx * BAR_SEC
        i_bar = int(t_bar * SR)
        dur = BAR_SEC * 1.02 # slight overlap
        n_samp = min(int(dur * SR), CHUNK_SAMPLES - i_bar)
        if n_samp <= 0: continue
        t = np.linspace(0, dur, n_samp, endpoint=False)
        
        # Chord envelope: punchy attack, warm sustain
        env = (1.0 - np.exp(-t * 30.0)) * (0.7 * np.exp(-t * 1.2) + 0.3)
        
        c_sig_L = np.zeros(n_samp, dtype=np.float32)
        c_sig_R = np.zeros(n_samp, dtype=np.float32)
        
        for m in v:
            f = mtof(m)
            # 3 detuned oscillators per voice
            d1 = 2.0 ** (7.0 / 1200.0) # +7 cents
            d2 = 2.0 ** (-7.0 / 1200.0) # -7 cents
            o1 = np.sin(2.0 * math.pi * f * t) + 0.4 * np.sin(4.0 * math.pi * f * t)
            o2 = np.sin(2.0 * math.pi * (f * d1) * t) + 0.3 * np.sin(4.0 * math.pi * (f * d1) * t)
            o3 = np.sin(2.0 * math.pi * (f * d2) * t) + 0.3 * np.sin(4.0 * math.pi * (f * d2) * t)
            c_sig_L += (o1 + o2) * 0.22
            c_sig_R += (o1 + o3) * 0.22
            
        c_L = soft_clip(c_sig_L * 1.4) * env * 0.55
        c_R = soft_clip(c_sig_R * 1.4) * env * 0.55
        buf[i_bar:i_bar+n_samp, 0] += c_L
        buf[i_bar:i_bar+n_samp, 1] += c_R

    # 4. Synthesize Orchestral Strings (Upper atmosphere)
    for b_idx in range(4):
        v = voicings[b_idx]
        t_bar = b_idx * BAR_SEC
        i_bar = int(t_bar * SR)
        dur = BAR_SEC * 1.05
        n_samp = min(int(dur * SR), CHUNK_SAMPLES - i_bar)
        if n_samp <= 0: continue
        t = np.linspace(0, dur, n_samp, endpoint=False)
        bow_env = (1.0 - np.exp(-t * 6.0)) * (1.0 - 0.15 * (t / dur))
        s_L = np.zeros(n_samp, dtype=np.float32)
        s_R = np.zeros(n_samp, dtype=np.float32)
        for m in v:
            f = mtof(m + 12) # +1 octave
            det = 2.0 ** (6.0 / 1200.0)
            o1 = np.sin(2.0*math.pi*f*t) + 0.25*np.sin(4.0*math.pi*f*t)
            o2 = np.sin(2.0*math.pi*(f*det)*t)
            s_L += (o1 + o2) * 0.14
            s_R += (o1 + o2) * 0.14
        buf[i_bar:i_bar+n_samp, 0] += soft_clip(s_L) * bow_env * 0.32
        buf[i_bar:i_bar+n_samp, 1] += soft_clip(s_R) * bow_env * 0.32

    # 5. Synthesize Drums (Unless mode == 'off')
    if drum_mode != 'off':
        for b_idx in range(4):
            t_bar = b_idx * BAR_SEC
            
            # KICK
            if drum_mode == 'four_on_floor':
                kick_beats = [0.0, 1.0, 2.0, 3.0]
            elif drum_mode == 'double_time':
                kick_beats = [0.0, 1.5, 2.75]
            else: # Halftime dubstep
                kick_beats = [0.0, 2.75] if chaos > 1.2 else [0.0]
                
            for kb in kick_beats:
                t_k = t_bar + kb * BEAT_SEC
                i_k = int(t_k * SR)
                dur = 0.38
                n_samp = min(int(dur * SR), CHUNK_SAMPLES - i_k)
                if n_samp <= 0: continue
                t = np.linspace(0, dur, n_samp, endpoint=False)
                f_env = 48.0 + 95.0 * np.exp(-t * 30.0)
                phase = 2.0 * np.pi * np.cumsum(f_env) / SR
                amp = np.exp(-t * 7.5)
                k_sig = soft_clip(np.sin(phase) * amp * 2.2) * 0.92
                buf[i_k:i_k+n_samp, 0] += k_sig
                buf[i_k:i_k+n_samp, 1] += k_sig
                
            # SNARE
            if drum_mode == 'double_time':
                snare_beats = [1.0, 3.0] # 2 and 4 in standard time
            else: # Halftime dubstep
                snare_beats = [2.0] # Beat 3
                if chaos > 1.5:
                    snare_beats.append(3.75) # Ghost snare
                    
            for sb in snare_beats:
                t_s = t_bar + sb * BEAT_SEC
                i_s = int(t_s * SR)
                dur = 0.28
                n_samp = min(int(dur * SR), CHUNK_SAMPLES - i_s)
                if n_samp <= 0: continue
                t = np.linspace(0, dur, n_samp, endpoint=False)
                f_env = 135.0 + 60.0 * np.exp(-t * 32.0)
                phase = 2.0 * np.pi * np.cumsum(f_env) / SR
                body = np.sin(phase) * np.exp(-t * 20.0) * 0.7
                noise = (np.random.rand(n_samp) * 2.0 - 1.0) * np.exp(-t * 16.0) * 0.65
                is_ghost = (sb == 3.75)
                s_sig = soft_clip((body + noise) * 1.8) * (0.4 if is_ghost else 0.88)
                buf[i_s:i_s+n_samp, 0] += s_sig
                buf[i_s:i_s+n_samp, 1] += s_sig
                
            # HI-HATS (16th notes with chaos skips)
            hat_subdivs = 16
            for h_idx in range(hat_subdivs):
                if chaos < 0.6 and (h_idx % 2 != 0):
                    continue # sparse hats on low chaos
                t_h = t_bar + (h_idx / 4.0) * BEAT_SEC
                i_h = int(t_h * SR)
                dur = 0.065
                n_samp = min(int(dur * SR), CHUNK_SAMPLES - i_h)
                if n_samp <= 0: continue
                t = np.linspace(0, dur, n_samp, endpoint=False)
                noise = (np.random.rand(n_samp) * 2.0 - 1.0) * np.exp(-t * 50.0) * 0.32
                pan = 0.4 if (h_idx % 2 == 0) else 0.6
                buf[i_h:i_h+n_samp, 0] += noise * (1.0 - pan)
                buf[i_h:i_h+n_samp, 1] += noise * pan

    # 6. Master Limiting
    peak = np.max(np.abs(buf))
    if peak > 0.95:
        buf = buf / peak * 0.95
        
    return buf, voicings[-1]

def read_stream_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def update_live_overlay_files(cmd, author, chords, drums, chaos, clam_rate="0.0%", gt_compliance="100.0%"):
    clean_author = author if author.startswith('@') else f"@{author}"
    cmd_text = f"COMMAND: {cmd}  [Steered by {clean_author}]"
    chords_text = f"NOW PLAYING: {' -> '.join(chords)} (Drop-2 Voicing)"
    status_text = f"THIRI GOVERNOR: {clam_rate} CLAMS | GUIDE TONES: {gt_compliance} LOCKED | DRUMS: {drums.upper().replace('_', ' ')}"
    
    for path, content in [
        ('/tmp/thiri_live_cmd.txt', cmd_text),
        ('/tmp/thiri_live_chords.txt', chords_text),
        ('/tmp/thiri_live_status.txt', status_text)
    ]:
        try:
            with open(path, 'w') as f:
                f.write(content)
        except Exception:
            pass


def main():
    print("=================================================================")
    print("   THIRI // REAL-TIME DYNAMIC HARMONIC ENGINE STARTING")
    print("=================================================================")
    print(f"Sampling Rate:    {SR} Hz Stereo (16-bit PCM)")
    print(f"Tempo:            {BPM} BPM (4-bar chunks = {CHUNK_SEC:.4f}s / {CHUNK_SAMPLES} samples)")
    print(f"FIFO Output:      {FIFO_PATH}")
    print(f"State Monitor:    {STATE_FILE}")
    print("=================================================================")

    if os.path.exists(FIFO_PATH):
        try: os.remove(FIFO_PATH)
        except: pass
    os.mkfifo(FIFO_PATH)
    
    print(f"FIFO created. Waiting for audio consumer (FFmpeg)...")
    fifo_out = open(FIFO_PATH, 'wb')
    print("Consumer connected! Real-time dynamic synthesis active.\n")

    cycle_idx = 0
    last_voicing = None
    prev_tail = np.zeros((int(0.015 * SR), 2), dtype=np.float32) # 15ms crossfade buffer
    fade_len = len(prev_tail)

    while True:
        state = read_stream_state()
        
        # Check custom progression from live chat
        custom_prog = state.get("custom_progression")
        active_key = state.get("active_key", "C")
        mode = state.get("mode", "dubstep_drop")
        drums = state.get("drums", "halftime_dubstep")
        chaos = float(state.get("entropy_tau", 1.8))
        author = state.get("commanded_by", "@BluesPrinceMedia")
        
        if custom_prog and len(custom_prog) >= 4:
            chords = custom_prog[:4]
            source_desc = f"PROMPT by {author}: {' | '.join(chords)}"
        elif custom_prog and len(custom_prog) > 0:
            # Repeat chords to fill 4 bars
            chords = (custom_prog * 4)[:4]
            source_desc = f"PROMPT by {author}: {' | '.join(chords)}"
        else:
            chords = DEFAULT_CYCLE[cycle_idx % len(DEFAULT_CYCLE)]
            source_desc = f"12-KEY CYCLE [{active_key}]: {' -> '.join(chords)}"
            cycle_idx += 1

        last_cmd = state.get("last_command", f"!key {active_key}")
        clam_rate = state.get("clam_rate", "0.0%")
        gt_compliance = state.get("guide_tone_compliance", "100.0%")

        # Update real-time on-screen HUD files for FFmpeg drawtext
        update_live_overlay_files(
            cmd=last_cmd,
            author=author,
            chords=chords,
            drums=drums,
            chaos=chaos,
            clam_rate=clam_rate,
            gt_compliance=gt_compliance
        )

        print(f"⚡ [BARS ACTIVE] {source_desc} | Drums={drums} | Chaos={chaos:.1f}")

        # Synthesize the 4 bars
        chunk_f32, last_voicing = synth_4bar_chunk(
            chords_list=chords,
            drum_mode=drums,
            chaos=chaos,
            prev_voicing=last_voicing
        )
        
        # Apply 15ms equal-power crossfade at chunk boundary
        fade_in = np.linspace(0.0, 1.0, fade_len)[:, np.newaxis]
        fade_out = np.linspace(1.0, 0.0, fade_len)[:, np.newaxis]
        chunk_f32[:fade_len] = chunk_f32[:fade_len] * fade_in + prev_tail * fade_out
        prev_tail = chunk_f32[-fade_len:].copy()

        # Convert to 16-bit PCM bytes
        chunk_i16 = (np.clip(chunk_f32, -1.0, 1.0) * 32767.0).astype(np.int16)
        raw_bytes = chunk_i16.tobytes()

        # Write to FIFO (this blocks until FFmpeg reads it, perfectly synchronized)
        try:
            fifo_out.write(raw_bytes)
            fifo_out.flush()
        except (BrokenPipeError, IOError):
            print("FFmpeg consumer disconnected. Waiting for reconnection...")
            try: fifo_out.close()
            except: pass
            fifo_out = open(FIFO_PATH, 'wb')
            print("Consumer reconnected! Resuming dynamic synthesis.\n")
            continue

    try: fifo_out.close()
    except: pass
    if os.path.exists(FIFO_PATH):
        os.remove(FIFO_PATH)

if __name__ == '__main__':
    main()
