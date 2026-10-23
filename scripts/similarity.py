"""Speaker similarity check with Chatterbox's own voice encoder. Runs inside chatterbox\\.venv.
Usage: python similarity.py <reference.wav> <candidate.wav> [<candidate2.wav> ...]
Prints cosine similarity (1.0 = identical speaker embedding). As a rough guide on this encoder:
same person, different recordings is usually above 0.80; different people usually below 0.65.
"""
import sys
import librosa, numpy as np
from chatterbox.models.voice_encoder import VoiceEncoder
from huggingface_hub import hf_hub_download
import torch

ve = VoiceEncoder()
ve.load_state_dict(torch.load(hf_hub_download("ResembleAI/chatterbox", "ve.pt"), map_location="cpu"))
ve.eval()

def emb(path):
    wav, _ = librosa.load(path, sr=16000)
    e = ve.embeds_from_wavs([wav], sample_rate=16000)
    e = np.asarray(e).reshape(-1)
    return e / np.linalg.norm(e)

ref = emb(sys.argv[1])
for c in sys.argv[2:]:
    print(f"{float(np.dot(ref, emb(c))):.3f}  {c}")
