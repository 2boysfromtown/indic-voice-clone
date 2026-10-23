"""Turn a raw recording of your own voice into a clean cloning reference.

Usage:  python -I scripts/prepare_ref.py <recording> --name me_ta_ad --lang ta [--start SS] [--max 14]

Writes refs/<name>.wav (mono 24 kHz, loudness-normalised, edge silence trimmed, cut at a
natural pause between 9 s and --max) and refs/<name>.txt (a Whisper transcript of exactly
that clip). Open the .txt and fix any wrong word: IndicF5 copies the voice best when the
transcript matches the clip word for word. Whisper cannot transcribe romanised
Tanglish/Hinglish well; for those, type the words yourself in Tamil or Devanagari script.
"""
import argparse, re, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
WHISPER_PY = ROOT / "chatterbox/.venv/Scripts/python.exe"  # has faster-whisper (install.ps1)

ap = argparse.ArgumentParser()
ap.add_argument("recording")
ap.add_argument("--name", required=True)
ap.add_argument("--lang", required=True, choices=["ta", "hi", "en"])
ap.add_argument("--start", default="0")
ap.add_argument("--max", type=float, default=14.0)
a = ap.parse_args()

refs = ROOT / "refs"
refs.mkdir(exist_ok=True)
wav, full = refs / f"{a.name}.wav", refs / f"_{a.name}_full.wav"
af = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
      "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse,"
      "highpass=f=70,loudnorm=I=-20:TP=-2:LRA=7")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", a.start, "-i", a.recording,
                "-af", af, "-ac", "1", "-ar", "24000", str(full)], check=True)

# end the clip at a natural pause between 9 s and --max so no word is cut in half
det = subprocess.run(["ffmpeg", "-v", "info", "-i", str(full), "-af", "silencedetect=noise=-38dB:d=0.22",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", det)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", det)]
good = [(s + e) / 2 for s, e in zip(starts, ends) if 9.0 <= (s + e) / 2 <= a.max]
cut = max(good) if good else a.max
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-t", f"{cut:.3f}",
                "-af", "afade=t=out:st=%.3f:d=0.08" % max(0, cut - 0.08), str(wav)], check=True)
full.unlink()
print(f"reference clip: {wav} ({cut:.1f} s, cut at {'a pause' if good else 'the max length'})")

# PyTorch already ships cublas, but faster-whisper's engine cannot see it on Windows until we say where it is.
# If the GPU still fails, fall back to the CPU: slower, same words.
code = ("import os, sys\n"
        "try:\n"
        "    import torch; os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), 'lib'))\n"
        "except Exception:\n"
        "    pass\n"
        "from faster_whisper import WhisperModel\n"
        "try:\n"
        "    m = WhisperModel('large-v3-turbo', device='cuda', compute_type='int8_float16')\n"
        "except Exception:\n"
        "    m = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')\n"
        "s, _ = m.transcribe(sys.argv[1], language=sys.argv[2])\n"
        "sys.stdout.reconfigure(encoding='utf-8'); print(' '.join(x.text.strip() for x in s))\n")
text = ""
if WHISPER_PY.exists():
    r = subprocess.run([str(WHISPER_PY), "-c", code, str(wav), a.lang], capture_output=True, text=True, encoding="utf-8")
    text = r.stdout.strip()
    if not text and r.stderr.strip():
        print("whisper could not run:", r.stderr.strip().splitlines()[-1][:160])
(refs / f"{a.name}.txt").write_text(text + "\n", encoding="utf-8")
print(f"transcript -> refs/{a.name}.txt:\n  {text or '(empty: type the exact words you said)'}")
