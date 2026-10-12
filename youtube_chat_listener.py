#!/usr/bin/env python3
"""YouTube Live Chat Listener for Interactive Lo-Fi Sanctuary
Connects directly to the live stream chat using pytchat (zero API keys).
Parses audience commands:
- !mantra <quote> [!voice <name>] (ElevenLabs voice affirmations with ducking)
- !voice <rachel|adam|aura|monk>
- !bowl (Triggers 432 Hz crystal singing bowl harmonic chime)
- !beat <on|off|lofi|mute> (Toggle drums)
- !prog <chords...> (Jazz chord steering)
- !bpm <60-90> (Adjust tempo)
- !key <note> (Modulate key)
- !chaos <0.2-2.0> (Harmonic density)
"""
import sys, os, time, json, re, hashlib, shutil
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, 'stream_state.json')
CACHE_DIR = os.path.join(HERE, 'cache', 'mantras')
VOICE_QUEUE_DIR = '/tmp/thiri_voice_queue'
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(VOICE_QUEUE_DIR, exist_ok=True)

# Curated ElevenLabs soothing voice IDs
ELEVEN_VOICES = {
    'rachel': '21m00Tcm4TlvDq8ikWAM',   # Calm, warm female
    'aura': 'XB0fDUnXU5ikFXAm1I05',     # Meditative, soft female
    'charlotte': 'XB0fDUnXU5ikFXAm1I05',
    'adam': 'pNInz6obpgDQGcFmaJgB',     # Deep, grounding male
    'monk': 'TxGEqnHWrfWFTfGW9XjX',     # Resonant, slow cadence male
    'marcus': 'TxGEqnHWrfWFTfGW9XjX'
}
DEFAULT_VOICE = 'rachel'

VALID_KEYS = {
    'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'GB', 'DB', 'C#', 
    'AB', 'G#', 'EB', 'D#', 'BB', 'A#', 'F'
}
KEY_MAP = {'GB': 'F#', 'C#': 'Db', 'G#': 'Ab', 'D#': 'Eb', 'A#': 'Bb'}

def normalize_key(k_raw):
    k = k_raw.strip().upper()
    if k in KEY_MAP: k = KEY_MAP[k]
    if k in VALID_KEYS:
        if len(k) == 2 and k[1] == 'B': return k[0] + 'b'
        return k
    return None

def init_state():
    default_state = {
        "active_key": "C",
        "tempo_bpm": 90.0,
        "entropy_tau": 1.0,
        "mode": "lofi_sanctuary",
        "drums": "lofi",
        "last_command": "INITIALIZED",
        "commanded_by": "@BluesPrinceMedia",
        "active_mantra": "Peace within, clarity around",
        "active_voice": "Rachel",
        "trigger_bowl": False,
        "updated_at": time.time()
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                existing = json.load(f)
                if isinstance(existing, dict):
                    default_state.update(existing)
                    return default_state
        except Exception:
            pass
            
    with open(STATE_FILE, 'w') as f:
        json.dump(default_state, f, indent=2)
    return default_state

def update_state(updates):
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
    except Exception:
        state = init_state()
        
    state.update(updates)
    state["updated_at"] = time.time()
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    return state

def synthesize_mantra(raw_text, voice_name='rachel'):
    """Synthesizes text using ElevenLabs API with phonetic rule and disk caching."""
    clean_text = raw_text.strip().strip('"').strip("'")
    if not clean_text:
        return None
        
    # Enforce THIRI -> "Theory" pronunciation rule for TTS
    tts_text = re.sub(r'\bthiri\b', 'Theory', clean_text, flags=re.IGNORECASE)
    
    voice_key = voice_name.lower().strip()
    voice_id = ELEVEN_VOICES.get(voice_key, ELEVEN_VOICES[DEFAULT_VOICE])
    
    # Hash based on clean written text and voice
    text_hash = hashlib.md5(f"{voice_id}_{tts_text.lower()}".encode('utf-8')).hexdigest()
    cached_wav = os.path.join(CACHE_DIR, f"{voice_key}_{text_hash}.wav")
    
    # 1. Check cache first (zero cost!)
    if os.path.exists(cached_wav) and os.path.getsize(cached_wav) > 1000:
        print(f"⚡ [CACHE HIT] Mantra found in cache: '{clean_text}' ({voice_key})")
        queue_dest = os.path.join(VOICE_QUEUE_DIR, f"{int(time.time()*1000)}_{text_hash}.wav")
        shutil.copyfile(cached_wav, queue_dest)
        return queue_dest
        
    # 2. Call ElevenLabs API if key is available
    api_key = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if not api_key:
        print(f"⚡ [NOTICE] ELEVENLABS_API_KEY not set. Displaying mantra on HUD without audio: '{clean_text}'")
        return None
        
    print(f"🎙️ [ELEVENLABS] Synthesizing mantra: '{clean_text}' with voice {voice_key}...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/wav"
    }
    payload = {
        "text": tts_text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75
        }
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            with open(cached_wav, 'wb') as f:
                f.write(resp.content)
            queue_dest = os.path.join(VOICE_QUEUE_DIR, f"{int(time.time()*1000)}_{text_hash}.wav")
            shutil.copyfile(cached_wav, queue_dest)
            print(f"✅ [ELEVENLABS] Synthesized & Queued: {queue_dest}")
            return queue_dest
        else:
            print(f"⚠️ [ELEVENLABS] API Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"⚠️ [ELEVENLABS] Request failed: {e}")
        
    return None

def parse_single_command(text, author_name):
    clean_author = author_name.lstrip('@')
    parts = text.split()
    if not parts:
        return None
    cmd = parts[0].lower()
    
    # 1. Spoken Affirmation / Mantra: !mantra <quote...> [!voice <name>]
    if cmd in ('!mantra', '!affirmation', '!meditate'):
        # Extract voice if specified
        voice = DEFAULT_VOICE
        mantra_body = text[len(parts[0]):].strip()
        v_match = re.search(r'!voice\s+([a-zA-Z0-9_-]+)', mantra_body, flags=re.IGNORECASE)
        if v_match:
            voice = v_match.group(1).lower()
            mantra_body = re.sub(r'!voice\s+[a-zA-Z0-9_-]+', '', mantra_body, flags=re.IGNORECASE).strip()
            
        clean_mantra = mantra_body.strip('"').strip("'")
        if len(clean_mantra) > 140:
            clean_mantra = clean_mantra[:137] + "..."
            
        if clean_mantra:
            # Trigger background synthesis / queueing
            synthesize_mantra(clean_mantra, voice)
            return {
                "active_mantra": clean_mantra,
                "active_voice": voice.capitalize(),
                "last_command": f"!mantra \"{clean_mantra}\"",
                "commanded_by": f"@{clean_author}"
            }

    # 2. Singing Bowl Trigger: !bowl / !chime / !bell
    elif cmd in ('!bowl', '!chime', '!bell', '!gong'):
        return {
            "trigger_bowl": True,
            "last_command": "!bowl (432 Hz crystal chime)",
            "commanded_by": f"@{clean_author}"
        }

    # 3. Drum / Beat Control: !beat <1-20|off|lofi> or !drums
    elif cmd in ('!beat', '!drums', '!drum'):
        sub = parts[1].lower() if len(parts) > 1 else 'on'
        if sub in ('off', 'mute', 'cut', 'stop', 'quiet'):
            return {
                "drums": "off",
                "active_beat": 0,
                "last_command": "!beat off",
                "commanded_by": f"@{clean_author}"
            }
        elif sub.isdigit():
            b_num = max(1, min(20, int(sub)))
            return {
                "drums": "lofi",
                "active_beat": b_num,
                "last_command": f"!beat #{b_num:02d}",
                "commanded_by": f"@{clean_author}"
            }
        elif sub in ('lofi', 'piano', '0', 'procedural'):
            return {
                "drums": "lofi",
                "active_beat": 0,
                "last_command": "!beat procedural",
                "commanded_by": f"@{clean_author}"
            }
        else:
            return {
                "drums": "lofi",
                "last_command": f"!beat {sub}",
                "commanded_by": f"@{clean_author}"
            }

    # 3B. Binaural Entrainment: !binaural <carrier_hz> or !theta <hz> / !alpha <hz>
    elif cmd in ('!binaural', '!theta', '!alpha') and len(parts) > 1:
        try:
            val = float(parts[1])
            if cmd == '!binaural':
                return {
                    "binaural_carrier_hz": max(100.0, min(963.0, val)),
                    "last_command": f"!binaural {val:.0f}Hz",
                    "commanded_by": f"@{clean_author}"
                }
            else:
                return {
                    "binaural_beat_hz": max(1.0, min(30.0, val)),
                    "last_command": f"{cmd} {val:.1f}Hz",
                    "commanded_by": f"@{clean_author}"
                }
        except ValueError:
            return None

    # 4. Tempo / BPM: !bpm <60-95>
    elif cmd in ('!bpm', '!tempo') and len(parts) > 1:
        try:
            val = float(parts[1])
            val = max(60.0, min(95.0, val)) # Clamp to lo-fi pocket
            return {
                "tempo_bpm": round(val, 1),
                "last_command": f"!bpm {val:.0f}",
                "commanded_by": f"@{clean_author}"
            }
        except ValueError:
            return None

    # 5. Modulate Key: !key <note>
    elif cmd == '!key' and len(parts) > 1:
        raw_key = parts[1]
        norm_key = normalize_key(raw_key)
        if norm_key:
            return {
                "active_key": norm_key,
                "last_command": f"!key {norm_key}",
                "commanded_by": f"@{clean_author}"
            }

    # 6. Drive Chord Progression: !prog <chords...>
    elif cmd in ('!prog', '!chords', '!chord') and len(parts) > 1:
        prog_raw = text[len(parts[0]):].strip()
        if '|' in prog_raw:
            chord_list = [c.strip() for c in prog_raw.split('|') if c.strip()]
        elif ',' in prog_raw:
            chord_list = [c.strip() for c in prog_raw.split(',') if c.strip()]
        else:
            chord_list = parts[1:]
            
        if chord_list:
            clean_str = ' | '.join(chord_list)
            return {
                "custom_progression": chord_list,
                "last_command": f"!prog {clean_str}",
                "commanded_by": f"@{clean_author}"
            }

    # 7. Chaos / Harmonic Density: !chaos <0.2 - 2.0>
    elif cmd in ('!chaos', '!temp', '!entropy') and len(parts) > 1:
        try:
            val = float(parts[1])
            val = max(0.2, min(2.0, val))
            return {
                "entropy_tau": round(val, 2),
                "last_command": f"!chaos {val:.1f}",
                "commanded_by": f"@{clean_author}"
            }
        except ValueError:
            return None
            
    return None

def parse_command(msg_text, author_name):
    text = msg_text.strip()
    if not text.startswith('!'):
        return None
        
    clean_author = author_name.lstrip('@')
    chunks = re.findall(r'(![a-zA-Z0-9_]+(?:(?!\s*![a-zA-Z0-9_]+).)*)', text)
    if not chunks:
        chunks = [text]
        
    combined_updates = {}
    commands_run = []
    
    for c in chunks:
        c_str = c.strip()
        if not c_str:
            continue
        update = parse_single_command(c_str, clean_author)
        if update:
            combined_updates.update(update)
            if "last_command" in update:
                commands_run.append(update["last_command"])
                
    if combined_updates:
        combined_updates["commanded_by"] = f"@{clean_author}"
        if commands_run:
            combined_updates["last_command"] = " + ".join(commands_run)
        return combined_updates
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 youtube_chat_listener.py <YOUTUBE_VIDEO_ID>")
        sys.exit(1)
        
    target = sys.argv[1].strip()
    if "youtube.com" in target or "youtu.be" in target:
        m = re.search(r'(?:v=|\/live\/|\.be\/)([a-zA-Z0-9_-]{11})', target)
        video_id = m.group(1) if m else target
    else:
        video_id = target
        
    print("=================================================================")
    print("   THIRI // LO-FI SANCTUARY CHAT LISTENER INITIALIZING")
    print("=================================================================")
    print(f"Connecting to YouTube Video ID: {video_id}")
    print(f"Writing state updates to:       {STATE_FILE}")
    print("Commands supported:             !mantra, !bowl, !beat, !bpm, !prog, !key")
    print("=================================================================")
    
    init_state()
    
    try:
        import pytchat
    except ImportError:
        print("Error: pytchat not installed. Run via the virtualenv python.")
        sys.exit(1)
        
    while True:
        try:
            chat = pytchat.create(video_id=video_id)
            print(f"Connected! Listening to live chat on stream {video_id}...\n")
            
            while chat.is_alive():
                for c in chat.get().sync_items():
                    author = c.author.name
                    msg = c.message
                    action = parse_command(msg, author)
                    if action:
                        new_state = update_state(action)
                        print(f"⚡ [PROMPT RECEIVED] @{author}: '{msg}'")
                        print(f"   -> State: Mantra='{new_state.get('active_mantra')}' | Chords={new_state.get('custom_progression')} | Beat={new_state.get('drums')}\n")
                time.sleep(1.0)
                
            print(f"[CHAT LISTENER] Disconnected from {video_id}. Reconnecting in 5 seconds...")
        except Exception as e:
            print(f"[CHAT LISTENER] Connection error for {video_id}: {e}. Retrying in 5 seconds...")
        time.sleep(5.0)

if __name__ == '__main__':
    main()
