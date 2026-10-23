"""IndicF5 worker (Tamil, Hindi and 9 more Indian languages). Runs inside indicf5\\.venv.
Usage: python engine_indicf5.py <jobs.json>
jobs.json = {"ref_wav": ..., "ref_text": ..., "items": [{"text": ..., "out": ...}, ...]}
"""
import json, sys
import numpy as np, soundfile as sf, torch
from transformers import AutoModel

job = json.load(open(sys.argv[1], encoding="utf-8"))
model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
if torch.cuda.is_available():
    model = model.to("cuda")
for it in job["items"]:
    audio = model(it["text"], ref_audio_path=job["ref_wav"], ref_text=job["ref_text"])
    audio = np.asarray(audio)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    sf.write(it["out"], audio.astype(np.float32), 24000)
    print("ok", it["out"], flush=True)
