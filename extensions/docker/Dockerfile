FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ARG USERNAME=ubuntu
ARG USER_UID=1000
ARG COMFYUI_REPO=https://github.com/comfyanonymous/ComfyUI.git
ARG COMFYUI_COMMIT=807538fe6c66bca8c91edbad14414fb4e109cbde

ENV DEBIAN_FRONTEND=noninteractive

# Install base packages: sudo, ssh, curl, git, build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo openssh-server curl wget git ca-certificates build-essential \
    python3 python3-venv python3-pip

# RUN rm -rf /var/lib/apt/lists/*

# Create user with sudo no-password
RUN groupadd --gid ${USER_UID} ${USERNAME} 2>/dev/null || true && \
    useradd --uid ${USER_UID} --gid ${USER_UID} -m -s /bin/bash ${USERNAME} && \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME}

# Configure SSH server
RUN mkdir -p /var/run/sshd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# Copy public key into container
USER ${USERNAME}
RUN mkdir -p /home/${USERNAME}/.ssh && chmod 700 /home/${USERNAME}/.ssh
COPY skillpilot-ssh-key.pub /home/${USERNAME}/.ssh/authorized_keys
USER root
RUN chown ${USERNAME}:${USER_UID} /home/${USERNAME}/.ssh/authorized_keys && \
    chmod 600 /home/${USERNAME}/.ssh/authorized_keys

# Install uv (Python)
USER ${USERNAME}
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/${USERNAME}/.local/bin:${PATH}"
ENV COMFYUI_INSTALL_PATH="/home/${USERNAME}/ComfyUI"

# Install nvm (Node.js)
ENV NVM_DIR="/home/${USERNAME}/.nvm"
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && \
    . "${NVM_DIR}/nvm.sh" && nvm install --lts

# Install ComfyUI at the pinned version used by the media workflows.
RUN git clone ${COMFYUI_REPO} "${COMFYUI_INSTALL_PATH}" && \
    cd "${COMFYUI_INSTALL_PATH}" && \
    git checkout ${COMFYUI_COMMIT} && \
    uv venv && \
    . .venv/bin/activate && \
    uv pip install --upgrade pip setuptools wheel && \
    uv pip install -r requirements.txt

USER root

WORKDIR /home/${USERNAME}

EXPOSE 22 8080 7860 8188

# Start sshd in foreground and sleep forever
CMD ["/usr/sbin/sshd", "-D"]
