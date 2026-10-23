---
name: my-voice
description: Speak any script in the user's own cloned voice, fully offline on their NVIDIA GPU, in Tamil, Hindi or English (voiceovers, ads, reels, podcasts). Uses the indic-voice-clone toolkit (AI4Bharat IndicF5 for Indian languages, Resemble Chatterbox for English). Use when the user says "my voice", "in my voice", "clone my voice", "voiceover in my voice", "offline voice clone", or gives a recording of themselves to clone.
---

# my-voice

Drives the `indic-voice-clone` folder (set `VOICE_ROOT` below to where the user cloned it).

## One-time setup
1. `powershell -ExecutionPolicy Bypass -File install.ps1` (Windows + NVIDIA; uv, ffmpeg, git on PATH).
2. The user accepts IndicF5's terms at https://huggingface.co/ai4bharat/IndicF5 and runs `chatterbox\.venv\Scripts\hf.exe auth login` themselves. Never handle their token.
3. The user records 10-14 s per language (read `examples/RECORDING-SCRIPTS.md`) into `recordings/`, then: `python -I scripts/prepare_ref.py recordings/me_ta_ad.m4a --name me_ta_ad --lang ta`. Check the transcript in `refs/*.txt` with the user; it must match the clip.

## Generate
`python -I scripts/speak.py --lang ta|hi|en --text "..." --out out/voice.wav`
- Defaults to the user's `me_<lang>_ad` reference; English uses exaggeration 0.7, cfg 0.3.
- Tamil and Hindi go to IndicF5, English to Chatterbox. Never route English to IndicF5: it keeps the voice but the words come out as gibberish.
- Write Tamil in Tamil script and Hindi in Devanagari; romanised text sounds worse.
- Check a result: `chatterbox\.venv\Scripts\python.exe scripts/similarity.py refs/me_en_ad.wav out/voice.wav` (above 0.85 is the same speaker; about 0.6 is a different person).

## Rules
- Only clone the user's own voice or someone with written consent.
- Chatterbox adds Resemble's inaudible Perth watermark to every file.
