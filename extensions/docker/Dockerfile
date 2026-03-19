FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y vim sudo tmux ffmpeg wget git curl git-lfs python3.10-dev openssh-server

# Create ubuntu user with sudo permission, using workspace /home/ubuntu/workspace
RUN useradd -m -s /bin/bash ubuntu && \
    echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    mkdir -p /home/ubuntu/workspace && \
    chown -R ubuntu:ubuntu /home/ubuntu

USER ubuntu
WORKDIR /home/ubuntu/workspace

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Miniconda
RUN wget -q https://repo.anaconda.com/miniconda/Miniconda3-py310_23.5.2-0-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    /bin/bash /tmp/miniconda.sh -b -p /home/ubuntu/miniconda3 && \
    rm /tmp/miniconda.sh

ENV PATH="/home/ubuntu/miniconda3/bin:$PATH"

# --- ComfyUI ---
RUN git clone https://github.com/comfy-org/ComfyUI ComfyUI && \
    cd ComfyUI && \
    git checkout f6b869d7d35f7160bf2fdeabaed378d737834540

RUN /home/ubuntu/.local/bin/uv venv /home/ubuntu/workspace/ComfyUI/.venv && \
    /home/ubuntu/.local/bin/uv pip install \
        --python /home/ubuntu/workspace/ComfyUI/.venv/bin/python \
        -r /home/ubuntu/workspace/ComfyUI/requirements.txt

# --- MuseTalk ---
RUN git clone https://github.com/TMElyralab/MuseTalk.git MuseTalk && \
    cd MuseTalk && \
    git checkout 0a89dec45a0192b824e3cf4daf96c239440c5ed8

RUN /bin/bash -c "\
    source /home/ubuntu/miniconda3/etc/profile.d/conda.sh && \
    conda create -n MuseTalk python==3.10 -y && \
    conda activate MuseTalk && \
    pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118 && \
    pip install -r /home/ubuntu/workspace/MuseTalk/requirements.txt && \
    pip install chumpy --no-build-isolation && \
    pip install --no-cache-dir -U openmim && \
    mim install mmengine && \
    mim install 'mmcv==2.0.1' && \
    mim install 'mmdet==3.1.0' && \
    mim install 'mmpose==1.1.0' --no-build-isolation && \
    pip install face_alignment && \
    pip install 'numpy==1.23.5'"

# --- SongBloom ---
RUN git clone https://github.com/tencent-ailab/SongBloom.git SongBloom && \
    cd SongBloom && \
    git checkout ef78022bfee6b571037d57c56152477699381d00

RUN /bin/bash -c "\
    source /home/ubuntu/miniconda3/etc/profile.d/conda.sh && \
    conda create -n SongBloom python==3.8.12 -y && \
    conda activate SongBloom && \
    pip install torch==2.2.0 torchaudio==2.2.0 --index-url https://download.pytorch.org/whl/cu118 && \
    pip install -r /home/ubuntu/workspace/SongBloom/requirements.txt"

# --- IndexTTS ---
RUN GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/index-tts/index-tts.git index-tts && \
    cd index-tts && \
    git checkout 830f6f8f94a51fea23ab1d639027a86200075a4e

RUN /home/ubuntu/.local/bin/uv sync --all-extras --project /home/ubuntu/workspace/index-tts

RUN /home/ubuntu/.local/bin/uv tool install "huggingface-hub[cli,hf_xet]"

# --- Scripts ---
COPY --chown=ubuntu:ubuntu download_models.sh /home/ubuntu/workspace/download_models.sh
COPY --chown=ubuntu:ubuntu entrypoint.sh /home/ubuntu/workspace/entrypoint.sh
RUN chmod +x /home/ubuntu/workspace/download_models.sh /home/ubuntu/workspace/entrypoint.sh

# ---
WORKDIR /home/ubuntu/workspace

EXPOSE 22 8080 7860 8188 

ENTRYPOINT ["/home/ubuntu/workspace/entrypoint.sh"]
