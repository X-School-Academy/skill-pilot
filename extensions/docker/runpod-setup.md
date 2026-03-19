Image: 

- nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04
- runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

```bash
bash -c 'apt update; \
DEBIAN_FRONTEND=noninteractive apt-get install openssh-server -y; \
mkdir -p ~/.ssh; \
cd ~/.ssh; \
chmod 700 ~/.ssh; \
echo "$PUBLIC_KEY" >> authorized_keys; \
chmod 700 authorized_keys; \
service ssh start; \
sleep infinity'
```


https://console.runpod.io/user/settings
API Keys
SSH Keys


curl -fsSL https://claude.ai/install.sh | bash
Location: ~/.local/bin/claude
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc


df -h
Filesystem                Size  Used Avail Use% Mounted on
overlay                   160G  106G   55G  66% /
tmpfs                      64M     0   64M   0% /dev
mfs#euro.runpod.net:9421  2.3P  1.4P  885T  62% /workspace
shm                        29G     0   29G   0% /dev/shm
/dev/sda2                 218G   28G  180G  14% /usr/bin/nvidia-smi
/dev/nvme0n1              3.7T  1.7T  2.0T  46% /etc/hosts
tmpfs                      26G   15M   26G   1% /run/nvidia-persistenced/socket
tmpfs                     4.0K  4.0K     0 100% /run/nvidia-ctk-hook
tmpfs                     126G     0  126G   0% /proc/acpi
tmpfs                     126G     0  126G   0% /proc/asound
tmpfs                     126G     0  126G   0% /proc/scsi
tmpfs                     126G     0  126G   0% /sys/devices/virtual/powercap
tmpfs                     126G     0  126G   0% /sys/firmware