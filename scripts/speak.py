"""Say any script in the user's own cloned voice, fully offline.

Usage:
  python -I speak.py --lang ta --ref me_ta --text "..."            -> out/<timestamp>.wav
  python -I speak.py --lang hi --ref me_hi --file script.txt --out out/ad.wav
  python -I speak.py --lang en --ref me_en --file script.txt --engine chatterbox

Engines: ta and hi default to IndicF5 (MIT, built for Indian languages);
en defaults to Chatterbox (MIT). --engine chatterbox also works for hi.
The script is split into sentences, each is generated, then joined with short
pauses and loudness-normalised to -16 LUFS (good for voiceover under music).
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# keep model weights on D: (C: is small); the HF login token stays in its default place
os.environ.setdefault("HF_HUB_CACHE", str(ROOT / ".hf-cache" / "hub"))
ENGINES = {
    "indicf5": (ROOT / "indicf5/.venv/Scripts/python.exe", ROOT / "scripts/engine_indicf5.py"),
    "chatterbox": (ROOT / "chatterbox/.venv/Scripts/python.exe", ROOT / "scripts/engine_chatterbox.py"),
    "chatterbox-turbo": (ROOT / "chatterbox/.venv/Scripts/python.exe", ROOT / "scripts/engine_chatterbox.py"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--lang", required=True, choices=["ta", "hi", "en"])
ap.add_argument("--ref", help="name of a clip in refs/ (without .wav); defaults to your ad take for the language")
ap.add_argument("--text")
ap.add_argument("--file")
ap.add_argument("--out")
ap.add_argument("--engine", choices=list(ENGINES))
ap.add_argument("--gap", type=float, default=0.28, help="pause between sentences, seconds")
ap.add_argument("--exaggeration", type=float, help="Chatterbox emotion, 0.25-1.0 (English default 0.7)")
ap.add_argument("--cfg", type=float, help="Chatterbox pacing/adherence; 0.3 = steadier (English default 0.3)")
a = ap.parse_args()

# Defaults: your "ad" take per language; English uses the punchier "ad energy" settings
# (exaggeration 0.7, cfg 0.3), which tested best on real recordings.
DEFAULT_REF = {"en": "me_en_ad", "hi": "me_hi_ad", "ta": "me_ta_ad"}
a.ref = a.ref or DEFAULT_REF[a.lang]
if a.exaggeration is None:
    a.exaggeration = 0.7 if a.lang == "en" else 0.5
if a.cfg is None:
    a.cfg = 0.3 if a.lang == "en" else 0.5

text = a.text if a.text else Path(a.file).read_text(encoding="utf-8")
engine = a.engine or ("chatterbox" if a.lang == "en" else "indicf5")
ref_wav = ROOT / "refs" / f"{a.ref}.wav"
ref_txt = ROOT / "refs" / f"{a.ref}.txt"
if not ref_wav.exists():
    sys.exit(f"missing {ref_wav}. Run prepare_ref.py on a recording first.")

# split on sentence ends (., !, ?, Devanagari danda, newlines); keep chunks under ~220 chars
parts = [p.strip() for p in re.split(r"(?<=[.!?।])\s+|\n+", text) if p.strip()]
chunks = []
for p in parts:
    while len(p) > 220:
        cut = p.rfind(",", 0, 220)
        cut = cut if cut > 60 else 220
        chunks.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
    if p:
        chunks.append(p)

out = Path(a.out) if a.out else ROOT / "out" / f"{time.strftime('%Y%m%d-%H%M%S')}_{a.lang}.wav"
out.parent.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp(prefix="voice_", dir=ROOT / "out"))
job = {"ref_wav": str(ref_wav), "ref_text": ref_txt.read_text(encoding="utf-8").strip() if ref_txt.exists() else "",
       "lang": a.lang, "exaggeration": a.exaggeration, "cfg_weight": a.cfg, "turbo": engine == "chatterbox-turbo",
       "items": [{"text": c, "out": str(tmp / f"{i:03d}.wav")} for i, c in enumerate(chunks)]}
if engine == "indicf5" and not job["ref_text"]:
    sys.exit(f"IndicF5 needs the words of the reference clip in {ref_txt}.")
(tmp / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
py, worker = ENGINES[engine]
print(f"{engine}: {len(chunks)} sentence(s) in the voice of '{a.ref}'")
subprocess.run([str(py), str(worker), str(tmp / "job.json")], check=True)

# join with pauses, normalise
inputs, filt = [], []
for i, it in enumerate(job["items"]):
    inputs += ["-i", it["out"]]
    filt.append(f"[{i}]aresample=24000,aformat=channel_layouts=mono,apad=pad_dur={a.gap}[s{i}]")
filt.append("".join(f"[s{i}]" for i in range(len(chunks))) + f"concat=n={len(chunks)}:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=9[o]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[o]", "-ar", "48000", str(out)], check=True)
for f in tmp.iterdir():
    f.unlink()
tmp.rmdir()
print(f"done -> {out}")
