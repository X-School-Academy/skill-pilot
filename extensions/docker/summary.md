# Summary

## Tasks Completed

### 1. Dockerfile Created
Created `/home/ubuntu/workspace/Dockerfile` based on `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` with:
- vim, sudo, tmux, ffmpeg, wget, git, curl installed
- uv package manager installed
- `ubuntu` user created with passwordless sudo and workspace at `/home/ubuntu/workspace`
- Miniconda3 installed at `/home/ubuntu/miniconda3`
- ComfyUI cloned and pinned to commit `f6b869d7d35f7160bf2fdeabaed378d737834540`
- ComfyUI Python dependencies installed via `uv pip install`
- MuseTalk cloned and pinned to commit `0a89dec45a0192b824e3cf4daf96c239440c5ed8`
- MuseTalk conda environment set up with all dependencies
- MuseTalk model weights downloaded via `download_weights.sh`

### 2. ComfyUI Installed
- Cloned from https://github.com/comfy-org/ComfyUI to `/home/ubuntu/workspace/ComfyUI`
- **Pinned git commit:** `f6b869d7d35f7160bf2fdeabaed378d737834540`
- **ComfyUI version:** 0.17.0
- **Frontend version:** 1.41.21
- All dependencies installed via `uv pip install --system -r requirements.txt`

### 3. ComfyUI Running
Started via tmux session `comfyui`:
```
tmux attach -t comfyui
```
Server accessible at: `http://0.0.0.0:8188`

### 4. MuseTalk Installed
- Cloned from https://github.com/TMElyralab/MuseTalk to `/home/ubuntu/workspace/MuseTalk`
- **Pinned git commit:** `0a89dec45a0192b824e3cf4daf96c239440c5ed8`
- Installed following README exactly using conda:
  - conda env `MuseTalk` with Python 3.10
  - PyTorch 2.0.1 + cu118
  - requirements.txt
  - MMLab packages via mim: mmengine, mmcv==2.0.1, mmdet==3.1.0, mmpose==1.1.0
  - face_alignment, numpy==1.23.5

### 5. MuseTalk Weights Downloaded
Run from `/home/ubuntu/workspace/MuseTalk`:
```bash
sh ./download_weights.sh
```
Models stored in `./models/`:
- `musetalk/` (v1.0 weights)
- `musetalkV15/` (v1.5 weights)
- `dwpose/`, `face-parse-bisent/`, `sd-vae/`, `syncnet/`, `whisper/`

### 6. MuseTalk Tested Successfully
Run from `/home/ubuntu/workspace/MuseTalk` with conda env activated:
```bash
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate MuseTalk
sh inference.sh v1.5 normal
```
Results saved to:
- `./results/test/v15/yongen_yongen.mp4`
- `./results/test/v15/yongen_eng.mp4`

Exit code: 0 ✅

## How to Run MuseTalk

```bash
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate MuseTalk
cd /home/ubuntu/workspace/MuseTalk
sh inference.sh v1.5 normal
```

### 7. SongBloom Installed
- Cloned from https://github.com/tencent-ailab/SongBloom to `/home/ubuntu/workspace/SongBloom`
- **Pinned git commit:** `ef78022bfee6b571037d57c56152477699381d00`
- Installed following README exactly using conda:
  - conda env `SongBloom` with Python 3.8.12
  - PyTorch 2.2.0 + torchaudio 2.2.0 (cu118)
  - `pip install -r requirements.txt`

#### To run SongBloom inference:
```bash
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate SongBloom
cd /home/ubuntu/workspace/SongBloom
source set_env.sh
python3 infer.py --input-jsonl example/test.jsonl
# For low VRAM GPUs:
python3 infer.py --input-jsonl example/test.jsonl --dtype bfloat16
```

### 8. IndexTTS Installed
- Cloned from https://github.com/index-tts/index-tts to `/home/ubuntu/workspace/index-tts`
- **Pinned git commit:** `830f6f8f94a51fea23ab1d639027a86200075a4e`
- **Version:** 2.0.0
- Installed using `uv` exclusively (as required by README — conda/pip not supported):
  - `git lfs install` (for LFS support)
  - `uv sync --all-extras`
  - Model weights downloaded via `uv run hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints`
- Note: LFS-tracked example wav files unavailable (upstream LFS budget exceeded); generated a synthetic test wav

#### To run IndexTTS inference:
```bash
cd /home/ubuntu/workspace/index-tts
PYTHONPATH="." uv run python -c "
from indextts.infer_v2 import IndexTTS2
tts = IndexTTS2(cfg_path='checkpoints/config.yaml', model_dir='checkpoints', use_cuda_kernel=False, use_torch_compile=False)
tts.infer(spk_audio_prompt='examples/voice_01.wav', text='Hello world.', output_path='gen.wav')
"
```

### 9. IndexTTS Tested Successfully
Run from `/home/ubuntu/workspace/index-tts`:
```bash
PYTHONPATH="." uv run python -c "
from indextts.infer_v2 import IndexTTS2
tts = IndexTTS2(cfg_path='checkpoints/config.yaml', model_dir='checkpoints', use_cuda_kernel=False, use_torch_compile=False)
tts.infer(spk_audio_prompt='examples/voice_01.wav', text='Hello, this is a test of IndexTTS.', output_path='gen.wav', verbose=True)
"
```
Result saved to: `./gen.wav`
Total inference time: ~23 seconds

Exit code: 0 ✅

Note: `use_torch_compile=True` requires `python3.10-dev` to be installed (triton compiles a CUDA utils C extension that needs `Python.h`). Fixed by adding `python3.10-dev` to Dockerfile apt packages.

## Notes
- TensorRT warning is expected (no TensorRT installed) — does not affect inference
- VAE safetensors warning is expected — falls back to pickle format (`.bin`) correctly
- Models are not included in Docker image; run `download_weights.sh` after first launch
