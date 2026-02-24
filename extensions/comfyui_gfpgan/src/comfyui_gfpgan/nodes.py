import os
import torch
import numpy as np
import cv2
import requests
from tqdm import tqdm

import folder_paths
import comfy.model_management as model_management

from .gfpganer import GFPGANer

FACE_DETECTION_MODEL_DIR = "face_detection"
FACE_RESTORATION_MODELS_DIR = "face_restoration"

# --- Model Download ---
# Set up the models directories for GFPGAN
model_detection_dir = os.path.join(folder_paths.models_dir, FACE_DETECTION_MODEL_DIR)
if not os.path.exists(model_detection_dir):
    os.makedirs(model_detection_dir)
folder_paths.folder_names_and_paths[FACE_DETECTION_MODEL_DIR] = ([model_detection_dir], folder_paths.supported_pt_extensions)
    
model_restoration_dir = os.path.join(folder_paths.models_dir, FACE_RESTORATION_MODELS_DIR)
if not os.path.exists(model_restoration_dir):
    os.makedirs(model_restoration_dir)
folder_paths.folder_names_and_paths[FACE_RESTORATION_MODELS_DIR] = ([model_restoration_dir], folder_paths.supported_pt_extensions)

# Dictionary of model names and their download URLs
MODEL_URLS = {
    "GFPGANv1.4.pth": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
    "GFPGANv1.3.pth": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth",
    "RestoreFormer.pth": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/RestoreFormer.pth",
    "codeformer.pth": "https://huggingface.co/alexgenovese/facerestore/resolve/main/codeformer.pth",
}

def download_model(model_name, save_dir):
    """Downloads a model if it doesn't exist."""
    url = MODEL_URLS.get(model_name)
    if not url:
        print(f"GFPGAN: URL for model '{model_name}' not found.")
        return

    save_path = os.path.join(save_dir, model_name)
    if os.path.exists(save_path):
        return

    print(f"GFPGAN: Downloading model '{model_name}' from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        
        with open(save_path, 'wb') as f, tqdm(
            desc=model_name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                bar.update(size)
        
        print(f"GFPGAN: Model '{model_name}' downloaded successfully to {save_path}")

    except Exception as e:
        print(f"GFPGAN: Failed to download model '{model_name}'. Error: {e}")
        # Clean up partial file if download fails
        if os.path.exists(save_path):
            os.remove(save_path)

class GFPGANRestorer:
    """
    A GFPGAN face restoration node for ComfyUI with automatic model downloading.
    """
    def __init__(self):
        self.gfpgan_model = None
        self.last_model_key = None

    @classmethod
    def INPUT_TYPES(s):  
        available_models = list(MODEL_URLS.keys())
        return {
            "required": {
                "image": ("IMAGE", {"desc": "Batch of video frames (RGB, 0-1) to restore."}),
                "model_name": (available_models, {"desc": "GFPGAN/RestoreFormer checkpoint to load."}),
            },
            "optional": {
                "detection_long_side": ("INT", {"default": 700, "min": 0, "max": 2048, "step": 32, "desc": "Resize longer edge to this many px for detection (<=0 keeps native)."}),
                "max_faces": ("INT", {"default": 2, "min": 1, "max": 8, "step": 1, "desc": "Process up to this many largest faces per frame."}),
                "skip_internal": ("INT", {"default": 0, "min": 0, "max": 20, "step": 1, "desc": "Process this many frames before skipping one; 0 disables skipping."}),
                "use_fp16": ("BOOLEAN", {"default": True, "desc": "Use half precision when running on CUDA."}),
                "restore_weight": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05, "desc": "Blend strength between original (0) and restored face (1). For CodeFormer this is fidelity w (0=quality, 1=detail)."}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK",)
    FUNCTION = "restore_face"
    CATEGORY = "restoration"

    def restore_face(
        self,
        image: torch.Tensor,
        model_name: str,
        detection_long_side: int = 700,
        max_faces: int = 2,
        skip_internal: int = 0,
        use_fp16: bool = True,
        restore_weight: float = 0.5,
    ):
        # --- Download model if needed ---
        download_model(model_name, model_restoration_dir)
        
        device = model_management.get_torch_device()

        face_restoration_model_path = folder_paths.get_full_path(FACE_RESTORATION_MODELS_DIR, model_name)

        # Load or reload model if necessary
        model_key = (model_name, bool(use_fp16) and device.type == 'cuda')
        if self.gfpgan_model is None or self.last_model_key != model_key:
            if self.gfpgan_model: del self.gfpgan_model; torch.cuda.empty_cache()

            lower_name = model_name.lower()
            if 'codeformer' in lower_name:
                arch = 'codeformer'
            elif 'restoreformer' in lower_name:
                arch = 'RestoreFormer'
            else:
                arch = 'clean'
            channel_multiplier = 2

            try:
                self.gfpgan_model = GFPGANer(
                    face_detection_model_path=model_detection_dir,
                    face_restoration_model_path=face_restoration_model_path,
                    arch=arch,
                    channel_multiplier=channel_multiplier,
                    device=device,
                    use_half=use_fp16,
                )
                self.last_model_key = model_key
            except Exception as e:
                print(f"GFPGAN: Failed to load model {model_name}. Error: {e}")
                return (image,)

        # --- Image Processing ---
        batch_size = image.shape[0]
        restored_images = []
        restored_masks = []
        skip_internal = max(0, int(skip_internal))
        max_faces = max(1, int(max_faces))
        detection_long_side = int(max(0, detection_long_side)) if detection_long_side is not None else None
        weight = float(np.clip(restore_weight, 0.0, 1.0))
        for i in range(batch_size):
            img_rgb_np = (255. * image[i].cpu().numpy()).astype(np.uint8)
            img_bgr_np = cv2.cvtColor(img_rgb_np, cv2.COLOR_RGB2BGR)

            skip_frame = skip_internal > 0 and ((i + 1) % (skip_internal + 1) == 0)
            process_frame = not skip_frame
            if process_frame:
                try:
                    restored_img, mask = self.gfpgan_model.enhance(
                        img_bgr_np,
                        weight=weight,
                        detection_size=detection_long_side,
                        max_faces=max_faces,
                    )
                except Exception as e:
                    print(f"GFPGAN: Error during enhancement: {e}")
                    restored_img = img_bgr_np
                    h, w, _ = restored_img.shape
                    mask = np.zeros((h, w), dtype=np.uint8)
            else:
                restored_img = img_bgr_np
                h, w, _ = restored_img.shape
                mask = np.zeros((h, w), dtype=np.uint8)

            restored_img_rgb = cv2.cvtColor(restored_img, cv2.COLOR_BGR2RGB)
            restored_tensor = torch.from_numpy(restored_img_rgb).float() / 255.0
            restored_images.append(restored_tensor)

            mask_tensor = torch.from_numpy(mask).float() / 255.0
            restored_masks.append(mask_tensor)

        output_images_tensor = torch.stack(restored_images).to("cpu")
        output_masks_tensor = torch.stack(restored_masks).to("cpu")
        return (output_images_tensor, output_masks_tensor,)

NODE_CLASS_MAPPINGS = {"GFPGANRestorer": GFPGANRestorer}
NODE_DISPLAY_NAME_MAPPINGS = {"GFPGANRestorer": "GFPGAN Face Restore"}
