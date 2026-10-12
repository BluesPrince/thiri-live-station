#!/usr/bin/env python3
"""
build_splice_stereo_20.py

Generates 20 brand new 4-layer Lo-Fi beats (80-95 BPM) using strictly 100% Splice samples:
- Layer 1: Drum Loop (Kick & Snare) -> Centered (monophonic center, pan = 0.0)
- Layer 2: Chordal / Melodic Loop -> Natural Stereo
- Layer 3: High Percussion (Shaker / Hi-Hat / Top) -> Panned LEFT (pan = -0.72)
- Layer 4: Mid Percussion (Djembe / Njembe / Bongo / Timbale / Rim) -> Panned RIGHT (pan = +0.72)
"""

import os
import glob
import json
import subprocess
import numpy as np
import soundfile as sf
import librosa

SPLICE_DIR = "/Users/bluesprincemedia/Splice/sounds/packs"
ARTIFACT_DIR = "/Users/bluesprincemedia/.gemini/antigravity/brain/3aa18ef8-84ef-473c-afaf-3097bcc89071"
DESKTOP_WAV = "/Users/bluesprincemedia/Desktop/Social Media Assets Manager/Lo-Fi 20 Beats & Live Radio Station/WAV - 24-bit Masters"
DESKTOP_MP3 = "/Users/bluesprincemedia/Desktop/Social Media Assets Manager/Lo-Fi 20 Beats & Live Radio Station/MP3 - Social Previews"
DESKTOP_CAT = "/Users/bluesprincemedia/Desktop/Social Media Assets Manager/Lo-Fi 20 Beats & Live Radio Station/Catalog & Metadata"
LIVE_STATION_AUDIO = "/Users/bluesprincemedia/code/thiri-live-station/audio/lofi_beats"

os.makedirs(DESKTOP_WAV, exist_ok=True)
os.makedirs(DESKTOP_MP3, exist_ok=True)
os.makedirs(DESKTOP_CAT, exist_ok=True)
os.makedirs(LIVE_STATION_AUDIO, exist_ok=True)

TARGET_SR = 48000

# Cache of all splice files for fast lookup
print("Indexing Splice sounds...")
all_splice_files = {}
for p in glob.glob(f"{SPLICE_DIR}/**/*.wav", recursive=True):
    bname = os.path.basename(p)
    if bname not in all_splice_files:
        all_splice_files[bname] = p

def resolve_file(name):
    if name in all_splice_files:
        return all_splice_files[name]
    matches = glob.glob(f"{SPLICE_DIR}/**/{name}", recursive=True)
    if matches:
        all_splice_files[name] = matches[0]
        return matches[0]
    raise FileNotFoundError(f"Cannot find Splice file: {name}")

RECIPES = [
    {
        "id": "01",
        "title": "Midnight Tape Keys & Jazz Ride",
        "target_bpm": 80,
        "key": "F minor",
        "drum": ("OS_LFC2_90_Drum_Loop_12__Kick_Snare_.wav", 90),
        "chord": ("CLF_80_Keys_TapePiano_Fm.wav", 80),
        "high_perc": ("SO_JC_80_top_loop_acoustic_ride_aqua.wav", 80),
        "mid_perc": ("SO_DR_80_perc_loop_bongo_emerald.wav", 80),
        "desc": "Capsun vintage tape piano with Alita Moses jazz ride left and organic bongo groove right."
    },
    {
        "id": "02",
        "title": "Dark Cello Bongo Meditation",
        "target_bpm": 80,
        "key": "D minor",
        "drum": ("SO_DR_85_drum_loop_almond_dry.wav", 85),
        "chord": ("RS3_1_80_Dm_cellos_pad1.wav", 80),
        "high_perc": ("SO_DR_80_top_loop_lime.wav", 80),
        "mid_perc": ("SO_DR_80_perc_loop_timbale_fennel.wav", 80),
        "desc": "Dark emotive cello pads anchored by crisp lime shaker left and fennel timbales right."
    },
    {
        "id": "03",
        "title": "Lucky Cat Rhodes & Lily Shaker",
        "target_bpm": 80,
        "key": "E minor",
        "drum": ("SO_DR_85_drum_loop_cerulean.wav", 85),
        "chord": ("RKU_RTJ3_80_electric_piano_loop_lucky_cat_Emin.wav", 80),
        "high_perc": ("SO_DR_80_top_loop_lily.wav", 80),
        "mid_perc": ("SO_DR_82_drum_loop_perc_azuki.wav", 82),
        "desc": "Tape Jams 3 vintage Rhodes, delicate lily top loop left, and azuki wood perc right."
    },
    {
        "id": "04",
        "title": "Hammond Dub & Timbale Pocket",
        "target_bpm": 80,
        "key": "G minor",
        "drum": ("SO_DR_85_drum_loop_chartreuse.wav", 85),
        "chord": ("SO_DR_80_hammond_chords_bashment_Gmin.wav", 80),
        "high_perc": ("DD_DUB_81_drums_loop_dub_kit_tambourine_percussion4.wav", 81),
        "mid_perc": ("SO_DR_82_drum_loop_perc_azure.wav", 82),
        "desc": "Deep Hammond organ chords, Horseman tambourines left, and azure percussion right."
    },
    {
        "id": "05",
        "title": "Babylon Wurli & Lychee Shaker",
        "target_bpm": 82,
        "key": "C major",
        "drum": ("KAELIN_ELLIS_85_drum_loop_learned_from_the_best.wav", 85),
        "chord": ("SO_DR_82_wurli_chords_babylon_Cmaj.wav", 82),
        "high_perc": ("SO_DR_82_top_loop_lychee.wav", 82),
        "mid_perc": ("MdL_82_percussion_loop_paperhearts.wav", 82),
        "desc": "Kaelin Ellis punchy kick/snare center, warm Babylon Wurli, lychee shaker left, paperhearts perc right."
    },
    {
        "id": "06",
        "title": "Cielo Acoustic Pick & Traveler Perc",
        "target_bpm": 82,
        "key": "Eb major",
        "drum": ("DD_DUB_87_drums_loop_dub_kete2.wav", 87),
        "chord": ("OSS_TBK_82_GUITAR_LOOP_CIELO_ACOUSTIC_PICKED_Eb.wav", 82),
        "high_perc": ("SO_DR_82_top_loop_magenta.wav", 82),
        "mid_perc": ("MdL_84_percussion_loop_traveler.wav", 84),
        "desc": "Lush picked acoustic guitar, magenta shaker left, and MdL traveler groove right."
    },
    {
        "id": "07",
        "title": "Babylon Horns & Dub Timbale",
        "target_bpm": 82,
        "key": "C major",
        "drum": ("DD_DUB_87_drums_loop_dub_kit_timbale_kete.wav", 87),
        "chord": ("SO_DR_82_horn_stack_babylon_melody_Cmaj.wav", 82),
        "high_perc": ("DD_DUB_81_drums_loop_dub_kit_tambourine_percussion_timbale2.wav", 81),
        "mid_perc": ("SO_DR_85_perc_loop_timbale_gold.wav", 85),
        "desc": "Reggae/lo-fi brass stack in stereo, vintage tambourines left, gold timbales right."
    },
    {
        "id": "08",
        "title": "Shhh Electric Piano & Fuchsia Djembe",
        "target_bpm": 85,
        "key": "C minor",
        "drum": ("SO_DR_85_drum_loop_alder_dry.wav", 85),
        "chord": ("LEX_LFL_85_electric_piano_loop_shhh_Cm.wav", 85),
        "high_perc": ("SO_DR_85_top_loop_magnolia.wav", 85),
        "mid_perc": ("SO_DR_85_perc_loop_djembe_fuchsia.wav", 85),
        "desc": "Lofi lullabies keys, magnolia shaker left, and fuchsia djembe knocks right."
    },
    {
        "id": "09",
        "title": "Kaelin Ellis Pocket & Ginger Djembe",
        "target_bpm": 85,
        "key": "G minor",
        "drum": ("KAELIN_ELLIS_85_drum_loop_learned_from_the_best.wav", 85),
        "chord": ("DIASPORA_classicriddims_melodic_loop_6_electric_guitar_rhythm_dancehall_80_bpm_Gmin.wav", 80),
        "high_perc": ("SO_DR_85_top_loop_mandarin.wav", 85),
        "mid_perc": ("SO_DR_85_perc_loop_djembe_ginger.wav", 85),
        "desc": "Punchy modern hip-hop drums, classic electric guitar skank, mandarin top left, ginger djembe right."
    },
    {
        "id": "10",
        "title": "Babylon Rhythm Guitar & Bongo Fern",
        "target_bpm": 85,
        "key": "C major",
        "drum": ("SO_DR_85_drum_loop_almond_dry.wav", 85),
        "chord": ("SO_DR_82_guitar_rhythm_babylon_Cmaj.wav", 82),
        "high_perc": ("OSS_LS1_89_TOP_LOOP_ISLAND_NEVE.wav", 89),
        "mid_perc": ("SO_DR_85_perc_loop_bongo_fern.wav", 85),
        "desc": "Warm C major guitar rhythm, Neve top loop left, and organic bongo fern right."
    },
    {
        "id": "11",
        "title": "Date Night Guitar & Horseman Dub Timbale",
        "target_bpm": 87,
        "key": "Ab minor",
        "drum": ("DD_DUB_87_drums_loop_dub_kete2.wav", 87),
        "chord": ("OSS_LS1_87_GUITAR_LOOP_DATENIGHT_ELECTRIC_STRUM_Abm.wav", 87),
        "high_perc": ("OSS_LS1_89_TOP_LOOP_ISLAND_RECALL.wav", 89),
        "mid_perc": ("DD_DUB_87_drums_loop_dub_kit_timbale_percussion1.wav", 87),
        "desc": "Soulful electric guitar strums, Island Recall top left, Horseman timbales right."
    },
    {
        "id": "12",
        "title": "Vintage Jazzy Hop & Afroshake",
        "target_bpm": 88,
        "key": "G# minor",
        "drum": ("VHB_88_Drum_Loop_Jazzy_1.wav", 88),
        "chord": ("FL_MVA_I_Hate_It_Vocal_Loop_Male_Fx_Background_88_G#min.wav", 88),
        "high_perc": ("PMDK_hihat_loop_94_wah_do_dem.wav", 94),
        "mid_perc": ("KRS_88_percussion_loop_afroshake.wav", 88),
        "desc": "Vintage 88 BPM hip-hop drums, ambient vocal chord wash, crisp hats left, afroshake perc right."
    },
    {
        "id": "13",
        "title": "Horseman Kete & Djembe Tape",
        "target_bpm": 88,
        "key": "A minor",
        "drum": ("DD_DUB_88_drums_loop_dub_kit_kete2.wav", 88),
        "chord": ("KRS_kit02_loop_dancehall_crown_pads_89_Amin.wav", 89),
        "high_perc": ("SO_JC_90_top_loop_acoustic_ride_aero.wav", 90),
        "mid_perc": ("SO_DR_85_perc_loop_djembe_tape.wav", 85),
        "desc": "Acoustic ride aero left, authentic analog tape djembe right, surrounded by crown synth pads."
    },
    {
        "id": "14",
        "title": "Crown Pads & Bongo Fig",
        "target_bpm": 89,
        "key": "A minor",
        "drum": ("DD_DUB_88_drums_loop_dub_kit_percussion3.wav", 88),
        "chord": ("KRS_kit02_loop_dancehall_crown_pads_89_Amin.wav", 89),
        "high_perc": ("OSS_LS1_89_TOP_LOOP_ISLAND_NEVE.wav", 89),
        "mid_perc": ("SO_DR_85_perc_loop_bongo_fig.wav", 85),
        "desc": "Hypnotic A minor pads, island top loop left, and deep bongo fig pattern right."
    },
    {
        "id": "15",
        "title": "Lo-Fi Cuts 2 & Matrix Keys",
        "target_bpm": 90,
        "key": "F minor",
        "drum": ("OS_LFC2_90_Drum_Loop_12__Kick_Snare_.wav", 90),
        "chord": ("CLF_90_Keys_Matrix_Fm.wav", 90),
        "high_perc": ("SS_SD_90_top_loop_lion.wav", 90),
        "mid_perc": ("DD_DUB_89_drums_loop_dub_kit_percussion2.wav", 89),
        "desc": "Origin Sound Lo-Fi Cuts 2 punchy center kick/snare, Capsun Matrix keys, lion shaker left, dub perc right."
    },
    {
        "id": "16",
        "title": "Chestpuncher & Guillaume Muschalle Guitar",
        "target_bpm": 90,
        "key": "D minor",
        "drum": ("KAELIN_ELLIS_90_drum_loop_chestpuncher.wav", 90),
        "chord": ("SS_GM_90_Electric_Guitar_Loop_Lofi_Forrest_Rhythimc_Groove_Dmin.wav", 90),
        "high_perc": ("SO_LI_90_top_loop_sint_ti_leaning_filtered.wav", 90),
        "mid_perc": ("DD_DUB_89_drums_loop_dub_kit_percussion4.wav", 89),
        "desc": "Kaelin Ellis heavy kick/snare center, jazz guitar musings, filtered top loop left, wood perc right."
    },
    {
        "id": "17",
        "title": "Lion Afro Dancehall & Flute",
        "target_bpm": 90,
        "key": "A minor",
        "drum": ("SS_SD_90_drum_loop_lion.wav", 90),
        "chord": ("SS_SD_90_flute_lion_melody_Amin.wav", 90),
        "high_perc": ("SSR_90_BPM_Top_Loop_49.wav", 90),
        "mid_perc": ("SS_SD_90_synth_lion_perc_Amin.wav", 90),
        "desc": "Iss 814 live flute melody, reggaeton high shaker left, afro synth percussion right."
    },
    {
        "id": "18",
        "title": "La Isla Stripped & Prayer Keys",
        "target_bpm": 90,
        "key": "F# minor",
        "drum": ("SO_LI_90_drum_loop_sint_ti_stripped.wav", 90),
        "chord": ("CLF_90_LoFi_PrayerKeys_F#m.wav", 90),
        "high_perc": ("SO_HZ_90_songstarter_rider_Dmin.wav", 90),
        "mid_perc": ("OS_LFC2_90_Drum_Loop_9__Perc_Tops_.wav", 90),
        "desc": "Capsun prayer keys, Sonoma rider top left, Lo-Fi Cuts 2 syncopated percussion right."
    },
    {
        "id": "19",
        "title": "Boom Bap Archives & Thumb Piano",
        "target_bpm": 91,
        "key": "G# minor",
        "drum": ("BBA_Drum_Lp_91_5.wav", 91),
        "chord": ("90BPM_G#minor_Spacious-Thumb-Piano-Loop.wav", 90),
        "high_perc": ("KRS_94_percussion_loop_hihat.wav", 94),
        "mid_perc": ("KRS_94_percussion_loop_rims.wav", 94),
        "desc": "Authentic 91 BPM boom bap drums center, kalimba thumb piano, hi-hats left, rim clicks right."
    },
    {
        "id": "20",
        "title": "Screwed Up Rhodes & Swing Sticks",
        "target_bpm": 95,
        "key": "D major",
        "drum": ("RT_Jazz_Drums_Jazz_Swing_Sticks_95_Loop_4_Drums_Andreas_Klein_95_loop.wav", 95),
        "chord": ("95BPM_Dmajor_Screwed-Up-Rhodes-Loop.wav", 95),
        "high_perc": ("SO_HZ_95_hat_loop_babygangsta.wav", 95),
        "mid_perc": ("DD_DUB_88_drums_loop_dub_kit_percussion1.wav", 88),
        "desc": "Andreas Klein acoustic jazz swing sticks center, lo-fi Rhodes, babygangsta hat left, dub perc right."
    }
]

def load_and_prep(file_name, orig_bpm, target_bpm, target_len_samples):
    p = resolve_file(file_name)
    data, sr = sf.read(p, dtype='float32')
    
    # Ensure stereo
    if data.ndim == 1:
        data = np.column_stack((data, data))
    
    # Resample to TARGET_SR if needed
    if sr != TARGET_SR:
        data = librosa.resample(data.T, orig_sr=sr, target_sr=TARGET_SR).T
    
    # Time-stretch if BPM differs
    if abs(orig_bpm - target_bpm) > 0.5:
        rate = float(target_bpm) / float(orig_bpm)
        # librosa time_stretch
        stretched = librosa.effects.time_stretch(data.T, rate=rate).T
        data = stretched
        
    # Tile or trim to exactly target_len_samples
    cur_len = len(data)
    if cur_len < target_len_samples:
        repeats = int(np.ceil(target_len_samples / cur_len))
        data = np.tile(data, (repeats, 1))[:target_len_samples]
    else:
        data = data[:target_len_samples]
        
    return data

def apply_panning(stereo_data, pan):
    """
    pan: -1.0 (Full Left) to +1.0 (Full Right), 0.0 (Center)
    Uses constant power panning:
    gain_L = cos((pan + 1) * pi / 4)
    gain_R = sin((pan + 1) * pi / 4)
    """
    # Sum to mono first to ensure clean panning placement
    mono = 0.5 * (stereo_data[:, 0] + stereo_data[:, 1])
    angle = (pan + 1.0) * (np.pi / 4.0)
    gain_l = np.cos(angle)
    gain_r = np.sin(angle)
    
    out_l = mono * gain_l
    out_r = mono * gain_r
    return np.column_stack((out_l, out_r))

def smooth_loop_edges(audio, fade_samples=512):
    """Applies micro-fade at start and end to prevent any clicks on repeat."""
    fade_in = np.linspace(0.0, 1.0, fade_samples)[:, np.newaxis]
    fade_out = np.linspace(1.0, 0.0, fade_samples)[:, np.newaxis]
    audio[:fade_samples] *= fade_in
    audio[-fade_samples:] *= fade_out
    return audio

def master_limiter(audio, ceiling_db=-0.3):
    """Soft saturation curve and peak limiter."""
    ceiling_linear = 10.0 ** (ceiling_db / 20.0)
    # Tanh soft saturation
    audio_sat = np.tanh(audio * 0.95) / 0.95
    peak = np.max(np.abs(audio_sat))
    if peak > ceiling_linear:
        audio_sat = audio_sat * (ceiling_linear / peak)
    return audio_sat

print(f"Starting generation of {len(RECIPES)} Splice 4-Layer Beats...")

catalog_entries = []

for idx, r in enumerate(RECIPES):
    bpm = r["target_bpm"]
    # 8 bars duration at target BPM: 8 * 4 * (60 / bpm)
    duration_sec = 32.0 * (60.0 / bpm)
    target_samples = int(duration_sec * TARGET_SR)
    
    print(f"[{idx+1}/20] Processing {r['id']} - {r['title']} ({bpm} BPM, {duration_sec:.2f}s)...")
    
    # 1. Drum (Kick & Snare) -> Centered Mono
    drum_raw = load_and_prep(r["drum"][0], r["drum"][1], bpm, target_samples)
    mono_drum = 0.5 * (drum_raw[:, 0] + drum_raw[:, 1])
    drum_centered = np.column_stack((mono_drum * 0.707, mono_drum * 0.707))
    # Normalize drum gain
    drum_peak = np.max(np.abs(drum_centered)) + 1e-6
    drum_centered = drum_centered * (0.82 / drum_peak)
    
    # 2. Chordal -> Natural Stereo
    chord_raw = load_and_prep(r["chord"][0], r["chord"][1], bpm, target_samples)
    chord_peak = np.max(np.abs(chord_raw)) + 1e-6
    chord_stereo = chord_raw * (0.68 / chord_peak)
    
    # 3. High Percussion -> Panned LEFT (-0.72)
    high_raw = load_and_prep(r["high_perc"][0], r["high_perc"][1], bpm, target_samples)
    high_panned = apply_panning(high_raw, pan=-0.72)
    high_peak = np.max(np.abs(high_panned)) + 1e-6
    high_panned = high_panned * (0.50 / high_peak)
    
    # 4. Mid Percussion -> Panned RIGHT (+0.72)
    mid_raw = load_and_prep(r["mid_perc"][0], r["mid_perc"][1], bpm, target_samples)
    mid_panned = apply_panning(mid_raw, pan=+0.72)
    mid_peak = np.max(np.abs(mid_panned)) + 1e-6
    mid_panned = mid_panned * (0.58 / mid_peak)
    
    # Combine 4 layers
    mix = drum_centered + chord_stereo + high_panned + mid_panned
    mix = smooth_loop_edges(mix, fade_samples=512)
    mix = master_limiter(mix, ceiling_db=-0.3)
    
    # Output file base name
    slug = r["title"].replace(" ", "_").replace("&", "and").replace("'", "").replace("#", "s")
    base_name = f"{r['id']}_{slug}"
    wav_name = f"{base_name}.wav"
    mp3_name = f"{base_name}.mp3"
    
    # 1. Save 24-bit WAV to Desktop
    out_wav_desktop = os.path.join(DESKTOP_WAV, wav_name)
    sf.write(out_wav_desktop, mix, TARGET_SR, subtype='PCM_24')
    
    # 2. Save WAV to Live Station repo
    out_wav_station = os.path.join(LIVE_STATION_AUDIO, wav_name)
    sf.write(out_wav_station, mix, TARGET_SR, subtype='PCM_24')
    
    # 3. Save WAV to Artifact Dir
    out_wav_artifact = os.path.join(ARTIFACT_DIR, wav_name)
    sf.write(out_wav_artifact, mix, TARGET_SR, subtype='PCM_24')
    
    # 4. Convert to 320k MP3 using ffmpeg
    out_mp3_desktop = os.path.join(DESKTOP_MP3, mp3_name)
    out_mp3_artifact = os.path.join(ARTIFACT_DIR, mp3_name)
    cmd = [
        "ffmpeg", "-y", "-i", out_wav_desktop,
        "-codec:a", "libmp3lame", "-b:a", "320k",
        out_mp3_desktop
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # Copy MP3 to artifact dir
    import shutil
    shutil.copy2(out_mp3_desktop, out_mp3_artifact)
    
    catalog_entries.append({
        "track_number": int(r["id"]),
        "id": r["id"],
        "title": r["title"],
        "bpm": bpm,
        "key": r["key"],
        "duration_seconds": round(duration_sec, 2),
        "spatial_mix": {
            "layer_1_drum_center": r["drum"][0],
            "layer_2_chordal_stereo": r["chord"][0],
            "layer_3_high_perc_left": r["high_perc"][0],
            "layer_4_mid_perc_right": r["mid_perc"][0]
        },
        "description": r["desc"],
        "wav_file": wav_name,
        "mp3_file": mp3_name
    })

# Save catalog JSON
catalog_json_path = os.path.join(DESKTOP_CAT, "splice_stereo_20_beats.json")
with open(catalog_json_path, "w") as f:
    json.dump(catalog_entries, f, indent=2)

artifact_json_path = os.path.join(ARTIFACT_DIR, "splice_stereo_20_beats.json")
with open(artifact_json_path, "w") as f:
    json.dump(catalog_entries, f, indent=2)

# Save markdown catalog
cat_md = ["# Splice Stereo Lo-Fi Beats: 20 Brand New 4-Layer Productions", ""]
cat_md.append("All 20 beats are produced **100% strictly from Splice samples**.")
cat_md.append("- **Kick & Snare (Layer 1):** Kept strictly **DEAD CENTER** (mono pan 0.0).")
cat_md.append("- **High Percussion (Layer 3):** Spanned **LEFT** (pan -0.72).")
cat_md.append("- **Mid Percussion (Layer 4):** Spanned **RIGHT** (pan +0.72).")
cat_md.append("- **Chordal Layer (Layer 2):** Lush natural **STEREO**.\n")
cat_md.append("| # | Title | BPM | Key | Drum (Center) | Chord (Stereo) | High Perc (Left) | Mid Perc (Right) |")
cat_md.append("|---|---|---|---|---|---|---|---|")

for c in catalog_entries:
    m = c["spatial_mix"]
    cat_md.append(f"| {c['id']} | **{c['title']}** | {c['bpm']} | {c['key']} | `{m['layer_1_drum_center'][:22]}...` | `{m['layer_2_chordal_stereo'][:22]}...` | `{m['layer_3_high_perc_left'][:22]}...` | `{m['layer_4_mid_perc_right'][:22]}...` |")

cat_md_str = "\n".join(cat_md)
with open(os.path.join(DESKTOP_CAT, "BEATS_CATALOG.md"), "w") as f:
    f.write(cat_md_str)
with open(os.path.join(ARTIFACT_DIR, "BEATS_CATALOG.md"), "w") as f:
    f.write(cat_md_str)

print("\nSUCCESS: All 20 Splice Stereo Beats generated and catalogs written!")
