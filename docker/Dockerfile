FROM ubuntu:noble-20260410

ARG DEBIAN_FRONTEND=noninteractive

ENV HOME=/home/ubuntu \
    SHELL=/bin/bash \
    PNPM_HOME=/home/ubuntu/.local/share/pnpm \
    PATH=/home/ubuntu/.local/bin:/home/ubuntu/.cargo/bin:/home/ubuntu/.local/share/pnpm/bin:/home/ubuntu/.local/share/pnpm:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    UV_LINK_MODE=copy \
    SKILL_PILOT_CONTAINER=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      build-essential \
      ca-certificates \
      cmake \
      curl \
      ffmpeg \
      g++ \
      git \
      git-lfs \
      gnupg \
      gxmessage \
      make \
      pkg-config \
      portaudio19-dev \
      procps \
      python3 \
      python3-pip \
      python3-venv \
      sudo \
      tmux \
      wget \
      xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN if ! id -u ubuntu >/dev/null 2>&1; then \
      useradd --create-home --shell /bin/bash ubuntu; \
    fi \
    && usermod -aG sudo ubuntu \
    && printf 'ubuntu ALL=(ALL) NOPASSWD:ALL\n' >/etc/sudoers.d/90-ubuntu-nopasswd \
    && chmod 0440 /etc/sudoers.d/90-ubuntu-nopasswd

USER ubuntu
WORKDIR /home/ubuntu

RUN git lfs install --skip-repo \
    && mkdir -p "${PNPM_HOME}" "${HOME}/.local/bin" \
    && curl -fsSL https://get.pnpm.io/install.sh | sh \
    && pnpm config set fetch-retries 5 \
    && pnpm config set fetch-timeout 300000 \
    && pnpm config set fetch-retry-mintimeout 10000 \
    && pnpm config set fetch-retry-maxtimeout 120000 \
    && pnpm env use --global lts \
    && for pkg in @openai/codex @google/gemini-cli @github/copilot opencode-ai; do \
      for attempt in 1 2 3; do \
        pnpm install -g "${pkg}" && break; \
        if [ "${attempt}" = "3" ]; then exit 1; fi; \
        sleep $((attempt * 15)); \
      done; \
    done \
    && curl -fsSL https://astral.sh/uv/install.sh | sh

ARG SKILL_PILOT_REPO=https://github.com/X-School-Academy/skill-pilot.git
ARG SKILL_PILOT_REF=codeware
RUN git clone --recurse-submodules --depth 1 --branch "${SKILL_PILOT_REF}" "${SKILL_PILOT_REPO}" /home/ubuntu/skill-pilot

WORKDIR /home/ubuntu/skill-pilot

RUN git lfs install \
    && git lfs pull || true

RUN uv --directory core/engine sync \
    && for attempt in 1 2 3; do \
      pnpm -C core/webui install --config.dangerouslyAllowAllBuilds=true && break; \
      if [ "${attempt}" = "3" ]; then exit 1; fi; \
      sleep $((attempt * 30)); \
    done \
    && ./skillpilot.sh build

COPY --chown=ubuntu:ubuntu entrypoint.sh /usr/local/bin/skill-pilot-entrypoint
RUN sudo chmod 0755 /usr/local/bin/skill-pilot-entrypoint

EXPOSE 3000 3001 3002 3003 5000 8000 8080

ENTRYPOINT ["sleep", "infinity"]
