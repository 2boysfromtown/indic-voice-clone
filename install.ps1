# One-command install for Windows + NVIDIA GPU.
# Needs on PATH: uv (https://docs.astral.sh/uv/), ffmpeg, git. NVIDIA driver 570+ (CUDA 12.8 wheels).
# Usage:  powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

# Keep Python, packages and models inside this folder (and off a small C: drive).
$env:UV_PYTHON_INSTALL_DIR = "$Root\python"
$env:UV_CACHE_DIR = "$Root\.uv-cache"
$env:UV_HTTP_TIMEOUT = "300"   # big wheels time out at the 30 s default

uv python install 3.10 3.11
$py310 = (Get-ChildItem "$Root\python" -Directory -Filter "cpython-3.10.*" | Select-Object -First 1).FullName + "\python.exe"
$py311 = (Get-ChildItem "$Root\python" -Directory -Filter "cpython-3.11.*" | Select-Object -First 1).FullName + "\python.exe"

# PyTorch 2.8 + CUDA 12.8 is required for RTX 50-series (Blackwell); older pins crash there.
"torch==2.8.0+cu128`ntorchaudio==2.8.0+cu128" | Out-File -Encoding ascii "$Root\overrides-chatterbox.txt"
"torch==2.8.0+cu128`ntorchaudio==2.8.0+cu128`ntransformers==4.49.0`ndatasets<3.4" | Out-File -Encoding ascii "$Root\overrides-indicf5.txt"
$idx = @("--extra-index-url", "https://download.pytorch.org/whl/cu128", "--index-strategy", "unsafe-best-match")

# English (and Hindi) engine: Chatterbox. setuptools<81 keeps pkg_resources for its watermarker.
uv venv chatterbox\.venv --python $py311 --seed
uv pip install --python chatterbox\.venv\Scripts\python.exe chatterbox-tts "setuptools<81" faster-whisper librosa --override overrides-chatterbox.txt @idx

# Tamil / Hindi / 9 more Indian languages: AI4Bharat IndicF5.
# transformers 5.x builds models on the meta device and IndicF5's remote code crashes, so pin 4.49.
uv venv indicf5\.venv --python $py310 --seed
uv pip install --python indicf5\.venv\Scripts\python.exe "git+https://github.com/ai4bharat/IndicF5.git" --override overrides-indicf5.txt @idx

& chatterbox\.venv\Scripts\python.exe -c "import torch; print('GPU ready:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
Write-Output ""
Write-Output "Installed. IndicF5 is gated on Hugging Face: accept its terms at https://huggingface.co/ai4bharat/IndicF5"
Write-Output "then log in once with:  chatterbox\.venv\Scripts\hf.exe auth login"
