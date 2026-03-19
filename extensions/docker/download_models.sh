#!/bin/bash
set -e

if [ -n "$NO_DOWNLOAD_MODELS" ]; then
    echo "=== NO_DOWNLOAD_MODELS is set, skipping model downloads ==="
    exit 0
fi

(
echo "=== Downloading MuseTalk weights ==="
cd /home/ubuntu/workspace/MuseTalk
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate MuseTalk
bash ./download_weights.sh
)

(
echo "=== Downloading IndexTTS-2 weights ==="
cd /home/ubuntu/workspace/index-tts
/home/ubuntu/.local/bin/uv run hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
)

echo "=== All models downloaded successfully ==="

