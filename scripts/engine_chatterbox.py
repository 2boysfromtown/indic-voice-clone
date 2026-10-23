"""Chatterbox worker (English, and Hindi via the multilingual model). Runs inside chatterbox\\.venv.
Usage: python engine_chatterbox.py <jobs.json>
jobs.json = {"ref_wav": ..., "lang": "en"|"hi", "exaggeration": 0.5, "cfg_weight": 0.5,
             "items": [{"text": ..., "out": ...}, ...]}
Every file carries Resemble's inaudible Perth watermark (built into the package).
"""
import json, sys
import torch, torchaudio as ta

job = json.load(open(sys.argv[1], encoding="utf-8"))
dev = "cuda" if torch.cuda.is_available() else "cpu"
lang = job.get("lang", "en")
kw = {"exaggeration": job.get("exaggeration", 0.5), "cfg_weight": job.get("cfg_weight", 0.5)}
if lang == "en" and job.get("turbo"):
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    model = ChatterboxTurboTTS.from_pretrained(device=dev)
    gen = lambda t: model.generate(t, audio_prompt_path=job["ref_wav"])
elif lang == "en":
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device=dev)
    gen = lambda t: model.generate(t, audio_prompt_path=job["ref_wav"], **kw)
else:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    model = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    gen = lambda t: model.generate(t, language_id=lang, audio_prompt_path=job["ref_wav"], **kw)
for it in job["items"]:
    wav = gen(it["text"])
    ta.save(it["out"], wav, model.sr)
    print("ok", it["out"], flush=True)
