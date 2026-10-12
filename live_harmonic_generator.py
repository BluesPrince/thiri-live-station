#!/usr/bin/env python3
"""
THIRI // 24/7 Interactive Lo-Fi Sanctuary Audio Generator Daemon
Continuously monitors stream_state.json and synthesizes 4-bar audio chunks
in real-time, streaming raw 16-bit 48kHz PCM directly into a named FIFO pipe.

Lo-Fi Sanctuary Features:
- Laid-back 78 BPM lo-fi hip hop groove with swing hi-hats and pillowy boom-bap drums.
- Warm Rhodes / Electric Piano chord voicings with Drop-2 jazz voice leading.
- Pure sine wave sub-bass (808 style) sitting deep in the 40-80 Hz pocket.
- Continuous authentic vinyl crackle and dust bed at -22 dB.
- 432 Hz crystal and Tibetan singing bowl harmonic chime triggers.
- Dynamic ElevenLabs spoken voice affirmation queue with -12 dB sidechain ducking.
- External Splice drum loop support (drop any WAV into /app/audio/drums/).
- Seamless equal-power boundary crossfades for 100% click-free continuity.
"""

import os, sys, time, json, math, re, itertools, wave, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, 'stream_state.json')
FIFO_PATH = '/tmp/thiri_live_audio.fifo'
VOICE_QUEUE_DIR = '/tmp/thiri_voice_queue'
DRUM_LOOPS_DIR = os.path.join(HERE, 'audio', 'drums')
os.makedirs(VOICE_QUEUE_DIR, exist_ok=True)
os.makedirs(DRUM_LOOPS_DIR, exist_ok=True)

SR = 48000
BPM = 78.0
BEAT_SEC = 60.0 / BPM
BAR_SEC = BEAT_SEC * 4.0
CHUNK_BARS = 4
CHUNK_SEC = CHUNK_BARS * BAR_SEC # ~12.307 seconds per 4 bars
CHUNK_SAMPLES = int(round(CHUNK_SEC * SR))

NOTE_NAMES = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5,
    'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11
}

# Default 12-key cycle of cozy 2-5-1s
DEFAULT_CYCLE = [
    ['Dm9', 'G13', 'Cmaj9', 'A7alt'],
    ['Cm9', 'F13', 'Bbmaj9', 'G7alt'],
    ['Bbm9', 'Eb13', 'Abmaj9', 'F7alt'],
    ['Abm9', 'Db13', 'Gbmaj9', 'Eb7alt'],
    ['F#m9', 'B13', 'Emaj9', 'C#7alt'],
    ['Em9', 'A13', 'Dmaj9', 'B7alt'],
    ['C#m9', 'F#13', 'Bmaj9', 'G#7alt'],
    ['Bm9', 'E13', 'Amaj9', 'F#7alt'],
    ['Am9', 'D13', 'Gmaj9', 'E7alt'],
    ['Gm9', 'C13', 'Fmaj9', 'D7alt'],
    ['Fm9', 'Bb13', 'Ebmaj9', 'C7alt'],
    ['Ebm9', 'Ab13', 'Dbmaj9', 'Bb7alt'],
]

def mtof(m):
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))

def soft_clip(x):
    return np.tanh(x)

def parse_chord(c_str):
    c = c_str.strip()
    m = re.match(r'^([A-G][b#]?)(.*)$', c)
    if not m:
        return 0, 'maj9', [4, 7, 11, 14]
    root_str, quality = m.group(1), m.group(2).lower()
    root = NOTE_NAMES.get(root_str.upper(), 0)
    
    if 'maj9' in quality or 'maj7' in quality or '^7' in quality or 'maj' in quality:
        intervals = [4, 7, 11, 14] # 3, 5, 7, 9
    elif '13' in quality:
        intervals = [4, 10, 14, 21] # 3, b7, 9, 13
    elif 'alt' in quality or '7alt' in quality:
        intervals = [4, 10, 13, 20] # 3, b7, b9, b13
    elif 'b9' in quality:
        intervals = [4, 10, 13, 7] # 3, b7, b9, 5
    elif '#11' in quality or '7#11' in quality:
        intervals = [4, 10, 18, 14] # 3, b7, #11, 9
    elif '-7' in quality or 'm7' in quality or 'min7' in quality or 'm9' in quality:
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
    # Deep sub-bass sitting between MIDI 36 (C2, 65 Hz) and MIDI 47 (B2)
    midi = 36 + (root % 12)
    if midi > 43: midi -= 12 # Keep in the deep 40-75 Hz sub pocket
    return midi

def read_wav_file(path, target_sr=48000):
    """Loads any WAV file and resamples to target_sr stereo float32."""
    if not os.path.exists(path):
        return None
    try:
        with wave.open(path, 'rb') as wf:
            n_ch = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            
            if sampwidth == 2:
                data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
            elif sampwidth == 4:
                data = np.frombuffer(raw, dtype=np.float32)
            else:
                return None
                
            if n_ch == 1:
                data = np.column_stack([data, data])
            else:
                data = data.reshape(-1, 2)
                
            if framerate != target_sr:
                orig_len = len(data)
                new_len = int(round(orig_len * (target_sr / framerate)))
                resampled = np.zeros((new_len, 2), dtype=np.float32)
                resampled[:, 0] = np.interp(np.linspace(0, orig_len, new_len, endpoint=False), np.arange(orig_len), data[:, 0])
                resampled[:, 1] = np.interp(np.linspace(0, orig_len, new_len, endpoint=False), np.arange(orig_len), data[:, 1])
                return resampled
            return data
    except Exception as e:
        print(f"[WAV LOADER] Error reading {path}: {e}")
        return None

def synth_4bar_chunk(chords_list, drum_mode='lofi', chaos=1.0, prev_voicing=None, trigger_bowl=False, bpm=78.0):
    """Synthesizes a 4-bar lo-fi arrangement chunk with vinyl bed, keys, sine sub, and drums."""
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4.0
    chunk_sec = 4 * bar_sec
    chunk_samples = int(round(chunk_sec * SR))
    
    buf = np.zeros((chunk_samples, 2), dtype=np.float32)
    
    # 1. Continuous Vinyl Crackle & Dust Bed (-22 dB)
    noise_L = np.random.normal(0, 0.012, chunk_samples).astype(np.float32)
    noise_R = np.random.normal(0, 0.012, chunk_samples).astype(np.float32)
    dust = np.zeros(chunk_samples, dtype=np.float32)
    num_clicks = int(chunk_sec * 6)
    click_indices = np.random.randint(0, chunk_samples, num_clicks)
    for idx in click_indices:
        c_len = min(int(SR * 0.0025), chunk_samples - idx)
        dust[idx:idx+c_len] += np.linspace(np.random.uniform(0.03, 0.09) * np.random.choice([-1, 1]), 0, c_len)
    buf[:, 0] += (noise_L + dust) * 0.18
    buf[:, 1] += (noise_R + dust) * 0.18
    
    # 2. Parse and solve voicings for the 4 bars
    voicings = []
    roots = []
    curr_v = prev_voicing
    for c_str in chords_list:
        r, q, ivs = parse_chord(c_str)
        curr_v = solve_drop2(r, ivs, curr_v)
        voicings.append(curr_v)
        roots.append(get_bass_midi(r))
        
    # 3. Synthesize Pure Sine Sub-Bass (Deep 808 Pocket)
    for b_idx in range(4):
        f0 = mtof(roots[b_idx])
        t_bar = b_idx * bar_sec
        # Lo-fi bass rhythm: beat 1 and beat 2.5
        hits = [(0.0, bar_sec * 0.62), (beat_sec * 2.5, bar_sec * 0.35)]
        for h_off, h_dur in hits:
            t_start = t_bar + h_off
            i_start = int(t_start * SR)
            n_samp = min(int(h_dur * SR), chunk_samples - i_start)
            if n_samp <= 0: continue
            t = np.linspace(0, h_dur, n_samp, endpoint=False)
            env = (1.0 - np.exp(-t * 22.0)) * np.exp(-t * 1.8)
            # Pure sine + soft 2nd harmonic for phone audibility
            sig = np.sin(2.0 * math.pi * f0 * t) + 0.18 * np.sin(4.0 * math.pi * f0 * t)
            sig = soft_clip(sig * 1.2) * env * 0.68
            buf[i_start:i_start+n_samp, 0] += sig
            buf[i_start:i_start+n_samp, 1] += sig

    # 4. Synthesize Warm Rhodes / Electric Piano Chords (Gentle chorus & low-pass warmth)
    for b_idx in range(4):
        v = voicings[b_idx]
        t_bar = b_idx * bar_sec
        i_bar = int(t_bar * SR)
        dur = bar_sec * 1.04
        n_samp = min(int(dur * SR), chunk_samples - i_bar)
        if n_samp <= 0: continue
        t = np.linspace(0, dur, n_samp, endpoint=False)
        
        # Soft Rhodes bell envelope
        bell_env = np.exp(-t * 5.5) * 0.35
        warm_env = np.exp(-t * 1.1) * 0.65
        env = (1.0 - np.exp(-t * 50.0)) * (bell_env + warm_env)
        
        c_sig_L = np.zeros(n_samp, dtype=np.float32)
        c_sig_R = np.zeros(n_samp, dtype=np.float32)
        
        # Subtle analog vibrato / chorus LFO
        lfo_L = np.sin(2.0 * math.pi * 4.2 * t) * (3.0 / 1200.0)
        lfo_R = np.cos(2.0 * math.pi * 4.2 * t) * (3.0 / 1200.0)
        
        for m in v:
            f = mtof(m)
            # Soft bell FM structure: carrier + 2nd overtone decay
            sig_L = (np.sin(2.0 * math.pi * f * (1.0 + lfo_L) * t) + 
                     0.3 * np.sin(4.0 * math.pi * f * t) * np.exp(-t * 7.0))
            sig_R = (np.sin(2.0 * math.pi * f * (1.0 + lfo_R) * t) + 
                     0.3 * np.sin(4.0 * math.pi * f * t) * np.exp(-t * 7.0))
            c_sig_L += sig_L * 0.22
            c_sig_R += sig_R * 0.22
            
        buf[i_bar:i_bar+n_samp, 0] += c_sig_L * env * 0.75
        buf[i_bar:i_bar+n_samp, 1] += c_sig_R * env * 0.75

    # 5. Drums (Check for external Splice drum loop first, else synthesize lo-fi boom bap)
    external_loop = None
    loop_candidates = glob.glob(os.path.join(DRUM_LOOPS_DIR, '*.wav'))
    if loop_candidates and drum_mode not in ('off', 'mute', 'cut'):
        external_loop = read_wav_file(loop_candidates[0], target_sr=SR)
        
    if external_loop is not None and drum_mode not in ('off', 'mute', 'cut'):
        # Loop external drum sample seamlessly across chunk
        loop_len = len(external_loop)
        for offset in range(0, chunk_samples, loop_len):
            rem = min(loop_len, chunk_samples - offset)
            buf[offset:offset+rem, :] += external_loop[:rem, :] * 0.72
    elif drum_mode not in ('off', 'mute', 'cut'):
        # Procedural Chill Lo-Fi Boom-Bap Drums
        for b_idx in range(4):
            t_bar = b_idx * bar_sec
            
            # KICK: Pillowy 808 kick on beat 1 and beat 2.5
            kick_beats = [0.0, 2.5] if chaos >= 0.7 else [0.0]
            for kb in kick_beats:
                t_k = t_bar + kb * beat_sec
                i_k = int(t_k * SR)
                dur = 0.42
                n_samp = min(int(dur * SR), chunk_samples - i_k)
                if n_samp <= 0: continue
                t = np.linspace(0, dur, n_samp, endpoint=False)
                f_env = 42.0 + 44.0 * np.exp(-t * 22.0)
                phase = 2.0 * np.pi * np.cumsum(f_env) / SR
                k_sig = np.sin(phase) * np.exp(-t * 6.5) * 0.72
                buf[i_k:i_k+n_samp, 0] += k_sig
                buf[i_k:i_k+n_samp, 1] += k_sig
                
            # SNARE: Soft vinyl snare on beat 2 and 4
            for sb in [1.0, 3.0]:
                t_s = t_bar + sb * beat_sec
                i_s = int(t_s * SR)
                dur = 0.30
                n_samp = min(int(dur * SR), chunk_samples - i_s)
                if n_samp <= 0: continue
                t = np.linspace(0, dur, n_samp, endpoint=False)
                body = np.sin(2.0 * math.pi * 175.0 * t) * np.exp(-t * 25.0) * 0.35
                noise = np.random.uniform(-1, 1, n_samp) * np.exp(-t * 16.0) * 0.26
                s_sig = (body + noise) * 0.58
                buf[i_s:i_s+n_samp, 0] += s_sig
                buf[i_s:i_s+n_samp, 1] += s_sig
                
            # HI-HATS: Swung 8th notes with humanized velocity
            for h in range(8):
                swing = 0.035 if (h % 2 == 1) else 0.0
                t_h = t_bar + (h * 0.5 + swing) * beat_sec
                i_h = int(t_h * SR)
                dur = 0.075
                n_samp = min(int(dur * SR), chunk_samples - i_h)
                if n_samp <= 0: continue
                t = np.linspace(0, dur, n_samp, endpoint=False)
                hat = np.random.uniform(-1, 1, n_samp) * np.exp(-t * 55.0) * (0.10 if h%2==1 else 0.16)
                buf[i_h:i_h+n_samp, 0] += hat
                buf[i_h:i_h+n_samp, 1] += hat * 0.85

    # 6. Crystal Singing Bowl Chime (432 Hz Downbeat Resonance)
    if trigger_bowl or (chaos > 1.4 and b_idx == 0):
        b_dur = min(8.0, chunk_sec)
        n_b = int(b_dur * SR)
        t_b = np.linspace(0, b_dur, n_b, endpoint=False)
        f_b = 432.0
        b_env = (1.0 - np.exp(-t_b * 3.5)) * np.exp(-t_b * 0.45)
        bowl_L = (np.sin(2.0 * math.pi * f_b * t_b) + 0.3 * np.sin(2.0 * math.pi * (f_b * 2) * t_b)) * b_env * 0.38
        bowl_R = (np.sin(2.0 * math.pi * (f_b + 2.0) * t_b) + 0.3 * np.sin(2.0 * math.pi * (f_b * 2) * t_b)) * b_env * 0.38
        buf[:n_b, 0] += bowl_L
        buf[:n_b, 1] += bowl_R

    # 7. Dynamic ElevenLabs Spoken Affirmation & Sidechain Ducking
    active_voice_file = None
    queue_files = sorted(glob.glob(os.path.join(VOICE_QUEUE_DIR, '*.wav')))
    if queue_files:
        active_voice_file = queue_files[0]
        
    if active_voice_file and os.path.exists(active_voice_file):
        voice_audio = read_wav_file(active_voice_file, target_sr=SR)
        if voice_audio is not None:
            v_len = min(len(voice_audio), chunk_samples)
            # Apply -12 dB sidechain ducking on the music bed during speech
            duck_env = np.ones(chunk_samples, dtype=np.float32)
            fade_samples = int(0.25 * SR) # 250ms ramp
            duck_env[:fade_samples] = np.linspace(1.0, 0.25, fade_samples)
            duck_env[fade_samples:v_len] = 0.25 # -12 dB gain
            if v_len + fade_samples <= chunk_samples:
                duck_env[v_len:v_len+fade_samples] = np.linspace(0.25, 1.0, fade_samples)
            else:
                duck_env[v_len:] = np.linspace(0.25, 1.0, chunk_samples - v_len)
                
            buf[:, 0] *= duck_env
            buf[:, 1] *= duck_env
            
            # Mix voice at pristine clarity
            buf[:v_len, 0] += voice_audio[:v_len, 0] * 1.15
            buf[:v_len, 1] += voice_audio[:v_len, 1] * 1.15
            
        # Clean up played voice file
        try: os.remove(active_voice_file)
        except: pass

    # 8. Master Warm Limiting
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

def update_live_overlay_files(cmd, author, chords, drums, bpm=78.0, mantra=None, voice=None):
    clean_author = author if author.startswith('@') else f"@{author}"
    if mantra:
        cmd_text = f"MANTRA: \"{mantra}\" [{voice or 'Rachel'}] (by {clean_author})"
    else:
        cmd_text = f"PROMPT: {cmd}  [Steered by {clean_author}]"
        
    chords_text = f"CHORDS: {' -> '.join(chords)}  |  TEMPO: {int(bpm)} BPM (Lo-Fi)"
    status_text = f"THIRI SANCTUARY: 432 Hz RESONANCE | VINYL CALM: ON | DRUMS: {drums.upper().replace('_', ' ')}"
    
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
    print("   THIRI // 24/7 LO-FI SANCTUARY & HARMONIC ENGINE STARTING")
    print("=================================================================")
    print(f"Sampling Rate:    {SR} Hz Stereo (16-bit PCM)")
    print(f"Tempo:            {BPM} BPM (4-bar chunks = {CHUNK_SEC:.4f}s / {CHUNK_SAMPLES} samples)")
    print(f"FIFO Output:      {FIFO_PATH}")
    print(f"State Monitor:    {STATE_FILE}")
    print(f"Voice Queue:      {VOICE_QUEUE_DIR}")
    print(f"Drums Directory:  {DRUM_LOOPS_DIR}")
    print("=================================================================")

    if os.path.exists(FIFO_PATH):
        try: os.remove(FIFO_PATH)
        except: pass
    os.mkfifo(FIFO_PATH)
    
    print(f"FIFO created. Waiting for audio consumer (FFmpeg)...")
    fifo_out = open(FIFO_PATH, 'wb')
    print("Consumer connected! Real-time lo-fi sanctuary active.\n")

    cycle_idx = 0
    last_voicing = None
    prev_tail = np.zeros((int(0.015 * SR), 2), dtype=np.float32) # 15ms crossfade buffer
    fade_len = len(prev_tail)

    while True:
        state = read_stream_state()
        
        custom_prog = state.get("custom_progression")
        active_key = state.get("active_key", "C")
        drums = state.get("drums", "lofi")
        chaos = float(state.get("entropy_tau", 1.0))
        bpm = float(state.get("tempo_bpm", BPM))
        author = state.get("commanded_by", "@BluesPrinceMedia")
        mantra = state.get("active_mantra")
        voice = state.get("active_voice")
        trigger_bowl = state.get("trigger_bowl", False)
        
        # Reset one-shot bowl trigger in state
        if trigger_bowl:
            state["trigger_bowl"] = False
            try:
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)
            except: pass

        if custom_prog and len(custom_prog) >= 4:
            chords = custom_prog[:4]
            source_desc = f"PROMPT by {author}: {' | '.join(chords)}"
        elif custom_prog and len(custom_prog) > 0:
            chords = (custom_prog * 4)[:4]
            source_desc = f"PROMPT by {author}: {' | '.join(chords)}"
        else:
            chords = DEFAULT_CYCLE[cycle_idx % len(DEFAULT_CYCLE)]
            source_desc = f"COZY CYCLE [{active_key}]: {' -> '.join(chords)}"
            cycle_idx += 1

        last_cmd = state.get("last_command", f"!prog {' | '.join(chords)}")

        update_live_overlay_files(
            cmd=last_cmd,
            author=author,
            chords=chords,
            drums=drums,
            bpm=bpm,
            mantra=mantra,
            voice=voice
        )

        print(f"⚡ [LO-FI BARS ACTIVE] {source_desc} | Drums={drums} | Tempo={bpm} BPM")

        chunk_f32, last_voicing = synth_4bar_chunk(
            chords_list=chords,
            drum_mode=drums,
            chaos=chaos,
            prev_voicing=last_voicing,
            trigger_bowl=trigger_bowl,
            bpm=bpm
        )
        
        # Apply 15ms equal-power crossfade at chunk boundary
        fade_in = np.linspace(0.0, 1.0, fade_len)[:, np.newaxis]
        fade_out = np.linspace(1.0, 0.0, fade_len)[:, np.newaxis]
        chunk_f32[:fade_len] = chunk_f32[:fade_len] * fade_in + prev_tail * fade_out
        prev_tail = chunk_f32[-fade_len:].copy()

        chunk_i16 = (np.clip(chunk_f32, -1.0, 1.0) * 32767.0).astype(np.int16)
        raw_bytes = chunk_i16.tobytes()

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
