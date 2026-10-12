#!/usr/bin/env python3
"""YouTube Live Chat Listener for Promptable Generative Audio
Connects directly to the live stream chat using pytchat (zero API keys).
Parses commands: !key <note>, !chaos <0.2-2.0>, !drop, !breakdown, !scores.
Updates stream_state.json to steer THIRI & Google Magenta in real time.
"""
import sys, os, time, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, 'stream_state.json')

VALID_KEYS = {
    'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'GB', 'DB', 'C#', 
    'AB', 'G#', 'EB', 'D#', 'BB', 'A#', 'F'
}

# Standard normalization
KEY_MAP = {
    'GB': 'F#', 'C#': 'Db', 'G#': 'Ab', 'D#': 'Eb', 'A#': 'Bb'
}

def normalize_key(k_raw):
    k = k_raw.strip().upper()
    if k in KEY_MAP:
        k = KEY_MAP[k]
    if k in VALID_KEYS:
        # Title case format: F#, Db, Bb, C
        if len(k) == 2 and k[1] == 'B':
            return k[0] + 'b'
        return k
    return None

def init_state():
    default_state = {
        "active_key": "C",
        "tempo_bpm": 140.0,
        "entropy_tau": 1.8,
        "mode": "dubstep_drop",
        "last_command": "INITIALIZED",
        "commanded_by": "@BluesPrinceMedia",
        "updated_at": time.time(),
        "clam_rate": "0.0%",
        "guide_tone_compliance": "100.0%"
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                existing = json.load(f)
                if isinstance(existing, dict) and "custom_progression" in existing:
                    return existing
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

def parse_single_command(text, author_name):
    clean_author = author_name.lstrip('@')
    parts = text.split()
    if not parts:
        return None
    cmd = parts[0].lower()
    
    # 1. Modulate Key: !key <note>
    if cmd == '!key' and len(parts) > 1:
        raw_key = parts[1]
        norm_key = normalize_key(raw_key)
        if norm_key:
            return {
                "active_key": norm_key,
                "last_command": f"!key {norm_key}",
                "commanded_by": f"@{author_name}"
            }
        else:
            print(f"  [IGNORE] Invalid key requested by @{author_name}: {raw_key}")
            return None
            
    # 2. Modulate Chaos / Entropy: !chaos <0.2 - 2.0> or !temp
    elif cmd in ('!chaos', '!temp', '!entropy') and len(parts) > 1:
        try:
            val = float(parts[1])
            val = max(0.2, min(2.0, val)) # Clamp to safe bounds
            return {
                "entropy_tau": round(val, 2),
                "last_command": f"!chaos {val:.1f}",
                "commanded_by": f"@{author_name}"
            }
        except ValueError:
            return None
            
    # 3. Solo Bell Breakdown / Mute Drums: !breakdown or !drums off
    elif cmd in ('!breakdown', '!mutedrums', '!nodrums'):
        return {
            "mode": "solo_breakdown",
            "drums": "off",
            "last_command": "!breakdown (drums muted)",
            "commanded_by": f"@{author_name}"
        }
        
    # 4. Halftime Dubstep Drop: !drop or !drums on
    elif cmd in ('!drop', '!drumsdrop'):
        return {
            "mode": "dubstep_drop",
            "drums": "halftime_dubstep",
            "last_command": "!drop (halftime dubstep)",
            "commanded_by": f"@{author_name}"
        }

    # 4b. Dedicated Drum Commands: !drums <pattern>
    elif cmd in ('!drums', '!drum'):
        sub = parts[1].lower() if len(parts) > 1 else 'on'
        if sub in ('off', 'mute', 'stop', 'cut'):
            return {
                "mode": "solo_breakdown",
                "drums": "off",
                "last_command": "!drums off",
                "commanded_by": f"@{author_name}"
            }
        elif sub in ('on', 'dubstep', 'halftime'):
            return {
                "mode": "dubstep_drop",
                "drums": "halftime_dubstep",
                "last_command": "!drums dubstep",
                "commanded_by": f"@{author_name}"
            }
        elif sub in ('four', 'house', 'techno', '4x4'):
            return {
                "mode": "four_on_the_floor",
                "drums": "four_on_floor",
                "last_command": "!drums four",
                "commanded_by": f"@{author_name}"
            }
        elif sub in ('trap', 'triplet', 'rolls'):
            return {
                "mode": "trap_groove",
                "drums": "trap_rolls",
                "last_command": "!drums trap",
                "commanded_by": f"@{author_name}"
            }
        elif sub in ('dnb', 'jungle', 'breakbeat', 'double'):
            return {
                "mode": "dnb_break",
                "drums": "double_time",
                "last_command": "!drums dnb",
                "commanded_by": f"@{author_name}"
            }
        else:
            return {
                "drums": sub,
                "last_command": f"!drums {sub}",
                "commanded_by": f"@{author_name}"
            }

    # 4c. Drum Density: !density <low|med|high|1-5>
    elif cmd in ('!density', '!groove') and len(parts) > 1:
        d_val = parts[1].lower()
        return {
            "drum_density": d_val,
            "last_command": f"!density {d_val}",
            "commanded_by": f"@{author_name}"
        }
        
    # 5. Drive Chord Progression: !prog <chords...> or !chord <chord>
    elif cmd in ('!prog', '!chords', '!chord') and len(parts) > 1:
        prog_raw = text[len(parts[0]):].strip()
        # Parse chords split by pipe, comma, or spaces
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
            
    return None

def parse_command(msg_text, author_name):
    text = msg_text.strip()
    if not text.startswith('!'):
        return None
        
    clean_author = author_name.lstrip('@')
    # Match each !command and its trailing arguments up until the next !command
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
        print("=================================================================")
        print("   THIRI // YOUTUBE LIVE CHAT PROMPT LISTENER")
        print("=================================================================")
        print("Usage: python3 youtube_chat_listener.py <YOUTUBE_VIDEO_ID_OR_URL>")
        print("Example: python3 youtube_chat_listener.py dQw4w9WgXcQ")
        print("=================================================================")
        sys.exit(1)
        
    target = sys.argv[1].strip()
    
    # Extract video ID from URL if full link passed
    if "youtube.com" in target or "youtu.be" in target:
        m = re.search(r'(?:v=|\/live\/|\.be\/)([a-zA-Z0-9_-]{11})', target)
        if m:
            video_id = m.group(1)
        else:
            print(f"Could not extract video ID from URL: {target}")
            sys.exit(1)
    else:
        video_id = target
        
    print("=================================================================")
    print("   THIRI // LIVE CHAT PROMPT LISTENER INITIALIZING")
    print("=================================================================")
    print(f"Connecting to YouTube Video ID: {video_id}")
    print(f"Writing state updates to:       {STATE_FILE}")
    print("Commands supported:             !key <note>, !chaos <0.2-2.0>, !drop, !breakdown")
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
            print(f"Connected! Listening to live comments on stream {video_id}...\n")
            
            while chat.is_alive():
                for c in chat.get().sync_items():
                    author = c.author.name
                    msg = c.message
                    action = parse_command(msg, author)
                    if action:
                        new_state = update_state(action)
                        print(f"⚡ [PROMPT RECEIVED] @{author}: '{msg}'")
                        print(f"   -> Updated state: Key={new_state.get('active_key')} | Chaos={new_state.get('entropy_tau')} | Mode={new_state.get('mode')}\n")
                time.sleep(1.0)
                
            print(f"[CHAT LISTENER] Disconnected from {video_id}. Reconnecting in 5 seconds...")
        except Exception as e:
            print(f"[CHAT LISTENER] Connection error for {video_id}: {e}. Retrying in 5 seconds...")
        time.sleep(5.0)

if __name__ == '__main__':
    main()
