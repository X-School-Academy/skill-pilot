https://huggingface.co/lightx2v/Wan2.2-NVFP4-Sparse

https://huggingface.co/Kijai/WanVideo_comfy_nvfp4

## ⚡ Performance Comparison

**Test Environment**: RTX 5090 Single GPU | LightX2V Framework | End-to-End Latency

| Resolution | Wan2.2-T2V-14B | Wan2.2-NVFP4-Sparse | Speedup |
| --- | ---: | ---: | ---: |
| 480p | 734s | 14.15s | 51.9x |
| 720p | 2668s | 45s | 59.3x |

## ⚠️ Notes

### System Requirements

- **Required Hardware**: NVIDIA RTX 50-series GPUs or other Blackwell architecture GPUs.
- **Recommended Runtime**: `lightx2v/lightx2v:26052801-cu130-5090`.

### Dependencies

- Prepare Wan2.2 T5 / VAE components following the standard LightX2V Wan2.2 model structure.
- Use Blackwell + NVFP4 kernels for optimal speed and memory efficiency.
