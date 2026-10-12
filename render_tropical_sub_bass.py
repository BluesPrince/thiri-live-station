#!/usr/bin/env python3
"""
create_deep_resonant_sub_bass.py

Transforms the sound of 15_Tropical_LoFi_Dancehall into a deep, low resonant
sine wavy bass with subtle saturation, blooming swell, and octave sub registers.
"""

import os
import subprocess
import numpy as np
import soundfile as sf
import scipy.signal as signal
import librosa

ORIG_CHORD_PATH = "/Users/bluesprincemedia/vibe-studio/out/sa3-chord-lora/dataset/heldout/Cs-minor-fm-bloom-pad-pulse.wav"
ORIG_FULL_MIX = "/Users/bluesprincemedia/code/thiri-live-station/audio/lofi_beats/15_Tropical_LoFi_Dancehall.wav"
DRUM_PATH = "/Users/bluesprincemedia/vibe-studio/out/g-blues-meditation-radio/stems/stem_splice_drums_full_92bpm.wav"
PERC_HIGH_PATH = "/Users/bluesprincemedia/Splice/sounds/packs/Dancehall Kingdom/Audio/LOOPS/Drum_&_Percussion_Loops/Hihat_Loops/PMDK_hihat_loop_94_wah_do_dem.wav"
PERC_MID_PATH = "/Users/bluesprincemedia/Splice/sounds/packs/Nairobi Rhythms/Black_Octopus_Sound_-_Nairobi_Rhythms_By_Digit_Music/Kit_Loops/123bpm_-_E_-_Nairobi/BOS_NR_123_Kit_Loop_Nairobi_Drums_Percussion.wav"

ARTIFACT_DIR = "/Users/bluesprincemedia/.gemini/antigravity/brain/3aa18ef8-84ef-473c-afaf-3097bcc89071"
DESKTOP_WAV = "/Users/bluesprincemedia/Desktop/Social Media Assets Manager/Lo-Fi 20 Beats & Live Radio Station/WAV - 24-bit Masters"
DESKTOP_MP3 = "/Users/bluesprincemedia/Desktop/Social Media Assets Manager/Lo-Fi 20 Beats & Live Radio Station/MP3 - Social Previews"
REPO_AUDIO = "/Users/bluesprincemedia/code/thiri-live-station/audio/lofi_beats"

TARGET_SR = 48000
BPM = 94.0
BAR_SEC = 4.0 * (60.0 / BPM) # 2.55319s per bar
TOTAL_SEC = 16.0 * (60.0 / BPM) # 10.21276s total (4 bars)
TOTAL_SAMPLES = int(round(TOTAL_SEC * TARGET_SR))

print(f"Target duration: {TOTAL_SEC:.3f}s ({TOTAL_SAMPLES} samples at {TARGET_SR}Hz)")

# -------------------------------------------------------------
# 1. PROCESS THE ORIGINAL SOUND INTO LOW RESONANT SINE BASS
# -------------------------------------------------------------
print("Loading original chord pad...")
chord_raw, sr = sf.read(ORIG_CHORD_PATH, dtype='float32')
if sr != TARGET_SR:
    chord_raw = librosa.resample(chord_raw.T, orig_sr=sr, target_sr=TARGET_SR).T
if chord_raw.ndim == 2:
    chord_mono = 0.5 * (chord_raw[:, 0] + chord_raw[:, 1])
else:
    chord_mono = chord_raw

# Loop or tile to 4 bars
if len(chord_mono) < TOTAL_SAMPLES:
    reps = int(np.ceil(TOTAL_SAMPLES / len(chord_mono)))
    chord_mono = np.tile(chord_mono, reps)[:TOTAL_SAMPLES]
else:
    chord_mono = chord_mono[:TOTAL_SAMPLES]

# Pitch shift down by 1 octave (-12) and 2 octaves (-24) to reach sub registers
print("Pitch shifting sound down into deep low octaves...")
chord_sub1 = librosa.effects.pitch_shift(chord_mono, sr=TARGET_SR, n_steps=-12)
chord_sub2 = librosa.effects.pitch_shift(chord_mono, sr=TARGET_SR, n_steps=-24)

# Resonant low-pass filter on the pitch-shifted audio to isolate the pure low sine resonance
# Cutoff at 95 Hz, 4th order Butterworth
b_low, a_low = signal.butter(4, 95.0 / (TARGET_SR / 2), btype='low')
chord_sub_filtered = signal.filtfilt(b_low, a_low, 0.6 * chord_sub1 + 0.4 * chord_sub2)

# -------------------------------------------------------------
# 2. SYNTHESIZE SUPER SUBWOOFY OCTAVE SINE WAVES WITH SWELL
# -------------------------------------------------------------
# Notes in C# Minor:
# Bar 1: C#1 (34.65 Hz) & C#2 (69.30 Hz)
# Bar 2: G#0 (25.96 Hz or 51.91 Hz G#1) & G#2 (103.83 Hz)
# Bar 3: C#1 & C#2
# Bar 4: G#1 & G#2
t = np.linspace(0, TOTAL_SEC, TOTAL_SAMPLES, endpoint=False)

# Build frequencies across 4 bars
freq_sub = np.zeros(TOTAL_SAMPLES)
freq_body = np.zeros(TOTAL_SAMPLES)
freq_oct3 = np.zeros(TOTAL_SAMPLES)

samples_per_bar = int(round(BAR_SEC * TARGET_SR))

# Bar 1: C# (34.65 Hz / 69.30 Hz)
freq_sub[:samples_per_bar] = 34.65
freq_body[:samples_per_bar] = 69.30
freq_oct3[:samples_per_bar] = 138.59

# Bar 2: G# (51.91 Hz / 103.83 Hz)
s2 = min(samples_per_bar * 2, TOTAL_SAMPLES)
freq_sub[samples_per_bar:s2] = 51.91
freq_body[samples_per_bar:s2] = 103.83
freq_oct3[samples_per_bar:s2] = 207.65

# Bar 3: C# (34.65 Hz / 69.30 Hz)
s3 = min(samples_per_bar * 3, TOTAL_SAMPLES)
freq_sub[s2:s3] = 34.65
freq_body[s2:s3] = 69.30
freq_oct3[s2:s3] = 138.59

# Bar 4: G# (51.91 Hz / 103.83 Hz)
freq_sub[s3:] = 51.91
freq_body[s3:] = 103.83
freq_oct3[s3:] = 207.65

# Generate continuous phase sine waves (no clicks at transitions)
phase_sub = 2.0 * np.pi * np.cumsum(freq_sub) / TARGET_SR
phase_body = 2.0 * np.pi * np.cumsum(freq_body) / TARGET_SR
phase_oct3 = 2.0 * np.pi * np.cumsum(freq_oct3) / TARGET_SR

sine_sub = np.sin(phase_sub)
sine_body = np.sin(phase_body)
sine_oct3 = np.sin(phase_oct3)

# -------------------------------------------------------------
# 3. CONSTRUCT THE BLOOMING SWELL ENVELOPE
# -------------------------------------------------------------
# Swell envelope per bar:
# Slow exponential bloom attack (swell) peaking around beat 2-3, gentle sustain & release
t_bar = np.linspace(0, BAR_SEC, samples_per_bar, endpoint=False)
# Swell curve: starts quiet (0.20), swells up smoothly to 1.0, releases slightly to 0.75
swell_curve = (0.20 + 0.80 * np.sin(np.pi * np.clip(t_bar / (BAR_SEC * 0.85), 0, 1) ** 0.8) ** 1.4)
# Repeat across 4 bars and match sine_sub length exactly
swell_env = np.tile(swell_curve, 5)[:len(sine_sub)]

# Apply swell to the sine components
sine_layer = (
    0.65 * sine_sub +       # Super subwoofy low register (34-52 Hz)
    0.40 * sine_body +      # Low resonant body octave (69-104 Hz)
    0.15 * sine_oct3        # Touch of upper octave definition (138-208 Hz)
) * swell_env

# Blend transformed original sound with the synthesized sine octave bass
chord_sub_filtered = chord_sub_filtered[:len(sine_sub)]
chord_sub_filtered = chord_sub_filtered / (np.max(np.abs(chord_sub_filtered)) + 1e-6)
combined_bass = 0.65 * sine_layer + 0.35 * (chord_sub_filtered * swell_env)

# -------------------------------------------------------------
# 4. TOUCH OF TAPE / TUBE SATURATION
# -------------------------------------------------------------
# Subtle soft-clip saturation for warmth and upper harmonic presence
drive = 1.35
saturated_bass = np.tanh(drive * combined_bass) / drive

# Low-frequency resonant peaking filter (EQ boost around 50 Hz, Q=1.5)
# to give that physical subwoofer vibration
b_peak, a_peak = signal.iirpeak(50.0 / (TARGET_SR / 2), Q=1.2)
sub_boosted = saturated_bass + 0.35 * signal.filtfilt(b_peak, a_peak, saturated_bass)

# Normalize solo sub bass to hit -0.8 dBFS peak
solo_bass = sub_boosted / (np.max(np.abs(sub_boosted)) + 1e-6) * (10.0 ** (-0.8 / 20.0))

# Stereo center image (mono bass centered in stereo track)
solo_bass_stereo = np.column_stack((solo_bass, solo_bass))

# Micro-fade edges to ensure click-free looping
fade_len = 512
fade_in = np.linspace(0, 1, fade_len)
fade_out = np.linspace(1, 0, fade_len)
solo_bass_stereo[:fade_len, 0] *= fade_in
solo_bass_stereo[:fade_len, 1] *= fade_in
solo_bass_stereo[-fade_len:, 0] *= fade_out
solo_bass_stereo[-fade_len:, 1] *= fade_out

# -------------------------------------------------------------
# 5. RENDER FULL PRODUCTION (DEEP BASS EDITION)
# -------------------------------------------------------------
print("Loading drum and percussion stems for full mix...")
def prep_stem(path, target_samples):
    data, s = sf.read(path, dtype='float32')
    if s != TARGET_SR:
        data = librosa.resample(data.T, orig_sr=s, target_sr=TARGET_SR).T
    if data.ndim == 1:
        data = np.column_stack((data, data))
    elif data.shape[1] > 2:
        data = data[:, :2]
    if len(data) < target_samples:
        reps = int(np.ceil(target_samples / len(data)))
        data = np.tile(data, (reps, 1))
    return data[:target_samples]

drum_data = prep_stem(DRUM_PATH, TOTAL_SAMPLES)
perc_high_data = prep_stem(PERC_HIGH_PATH, TOTAL_SAMPLES)
perc_mid_data = prep_stem(PERC_MID_PATH, TOTAL_SAMPLES)

# Kick & Snare dead center
drum_mono = 0.5 * (drum_data[:, 0] + drum_data[:, 1])
drum_center = np.column_stack((drum_mono * 0.707, drum_mono * 0.707))
drum_center = drum_center / (np.max(np.abs(drum_center)) + 1e-6) * 0.78

# High perc panned Left (-0.70)
angle_l = (-0.70 + 1.0) * (np.pi / 4.0)
high_mono = 0.5 * (perc_high_data[:, 0] + perc_high_data[:, 1])
high_panned = np.column_stack((high_mono * np.cos(angle_l), high_mono * np.sin(angle_l)))
high_panned = high_panned / (np.max(np.abs(high_panned)) + 1e-6) * 0.48

# Mid perc panned Right (+0.70)
angle_r = (0.70 + 1.0) * (np.pi / 4.0)
mid_mono = 0.5 * (perc_mid_data[:, 0] + perc_mid_data[:, 1])
mid_panned = np.column_stack((mid_mono * np.cos(angle_r), mid_mono * np.sin(angle_r)))
mid_panned = mid_panned / (np.max(np.abs(mid_panned)) + 1e-6) * 0.55

# Original chord layer slightly lowered to give massive room for the sub bass
orig_chord_stereo = prep_stem(ORIG_CHORD_PATH, TOTAL_SAMPLES)
orig_chord_stereo = orig_chord_stereo / (np.max(np.abs(orig_chord_stereo)) + 1e-6) * 0.42

# Blend full mix: Center Kick + Deep Sub Bass + Chords + Left/Right Perc
full_mix = drum_center + (solo_bass_stereo * 0.85) + orig_chord_stereo + high_panned + mid_panned

# Master soft saturation limiter
full_mix_sat = np.tanh(full_mix * 0.95) / 0.95
peak = np.max(np.abs(full_mix_sat))
ceiling = 10.0 ** (-0.3 / 20.0) # -0.3 dBFS True Peak
if peak > ceiling:
    full_mix_sat = full_mix_sat * (ceiling / peak)

full_mix_sat[:fade_len, 0] *= fade_in
full_mix_sat[:fade_len, 1] *= fade_in
full_mix_sat[-fade_len:, 0] *= fade_out
full_mix_sat[-fade_len:, 1] *= fade_out

# -------------------------------------------------------------
# 6. EXPORT ALL DELIVERABLES (WAV & MP3)
# -------------------------------------------------------------
print("Exporting audio files...")

# File 1: Solo Sub Bass
solo_wav_name = "15_Tropical_LoFi_Dancehall_Deep_Resonant_Sine_Bass_Solo.wav"
solo_mp3_name = "15_Tropical_LoFi_Dancehall_Deep_Resonant_Sine_Bass_Solo.mp3"

solo_wav_desktop = os.path.join(DESKTOP_WAV, solo_wav_name)
solo_mp3_desktop = os.path.join(DESKTOP_MP3, solo_mp3_name)
solo_wav_artifact = os.path.join(ARTIFACT_DIR, solo_wav_name)
solo_mp3_artifact = os.path.join(ARTIFACT_DIR, solo_mp3_name)
solo_wav_repo = os.path.join(REPO_AUDIO, solo_wav_name)

sf.write(solo_wav_desktop, solo_bass_stereo, TARGET_SR, subtype='PCM_24')
sf.write(solo_wav_artifact, solo_bass_stereo, TARGET_SR, subtype='PCM_24')
sf.write(solo_wav_repo, solo_bass_stereo, TARGET_SR, subtype='PCM_24')

subprocess.run(["ffmpeg", "-y", "-i", solo_wav_desktop, "-codec:a", "libmp3lame", "-b:a", "320k", solo_mp3_desktop],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
subprocess.run(["ffmpeg", "-y", "-i", solo_wav_desktop, "-codec:a", "libmp3lame", "-b:a", "320k", solo_mp3_artifact],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# File 2: Full Mix with Deep Sub Bass
full_wav_name = "15_Tropical_LoFi_Dancehall_Deep_Bass_Edition.wav"
full_mp3_name = "15_Tropical_LoFi_Dancehall_Deep_Bass_Edition.mp3"

full_wav_desktop = os.path.join(DESKTOP_WAV, full_wav_name)
full_mp3_desktop = os.path.join(DESKTOP_MP3, full_mp3_name)
full_wav_artifact = os.path.join(ARTIFACT_DIR, full_wav_name)
full_mp3_artifact = os.path.join(ARTIFACT_DIR, full_mp3_name)
full_wav_repo = os.path.join(REPO_AUDIO, full_wav_name)

sf.write(full_wav_desktop, full_mix_sat, TARGET_SR, subtype='PCM_24')
sf.write(full_wav_artifact, full_mix_sat, TARGET_SR, subtype='PCM_24')
sf.write(full_wav_repo, full_mix_sat, TARGET_SR, subtype='PCM_24')

subprocess.run(["ffmpeg", "-y", "-i", full_wav_desktop, "-codec:a", "libmp3lame", "-b:a", "320k", full_mp3_desktop],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
subprocess.run(["ffmpeg", "-y", "-i", full_wav_desktop, "-codec:a", "libmp3lame", "-b:a", "320k", full_mp3_artifact],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

print("SUCCESS: Solo Deep Resonant Bass and Full Deep Bass Edition rendered successfully!")
