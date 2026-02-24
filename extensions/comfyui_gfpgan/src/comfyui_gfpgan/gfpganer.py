import cv2
import os
import torch
import numpy as np
import warnings
from contextlib import nullcontext
from basicsr.utils import img2tensor, tensor2img
from .face_restore_helper import FaceRestoreHelper
from torchvision.transforms.functional import normalize
from .codeformer_arch import CodeFormer

from gfpgan.archs.gfpgan_bilinear_arch import GFPGANBilinear
from gfpgan.archs.gfpganv1_arch import GFPGANv1
from gfpgan.archs.gfpganv1_clean_arch import GFPGANv1Clean

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class GFPGANer():
    def __init__(self, face_detection_model_path, face_restoration_model_path, arch='clean', channel_multiplier=2, device=None, use_half=False):
        # initialize model
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if device is None else device
        self.use_half = bool(use_half) and self.device.type == 'cuda'
        self.model_arch = arch
        # initialize the GFP-GAN
        if arch == 'clean':
            self.gfpgan = GFPGANv1Clean(
                out_size=512,
                num_style_feat=512,
                channel_multiplier=channel_multiplier,
                decoder_load_path=None,
                fix_decoder=False,
                num_mlp=8,
                input_is_latent=True,
                different_w=True,
                narrow=1,
                sft_half=True)
        elif arch == 'bilinear':
            self.gfpgan = GFPGANBilinear(
                out_size=512,
                num_style_feat=512,
                channel_multiplier=channel_multiplier,
                decoder_load_path=None,
                fix_decoder=False,
                num_mlp=8,
                input_is_latent=True,
                different_w=True,
                narrow=1,
                sft_half=True)
        elif arch == 'original':
            self.gfpgan = GFPGANv1(
                out_size=512,
                num_style_feat=512,
                channel_multiplier=channel_multiplier,
                decoder_load_path=None,
                fix_decoder=True,
                num_mlp=8,
                input_is_latent=True,
                different_w=True,
                narrow=1,
                sft_half=True)
        elif arch == 'RestoreFormer':
            from gfpgan.archs.restoreformer_arch import RestoreFormer
            self.gfpgan = RestoreFormer()
        elif arch == 'codeformer':
            # CodeFormer fidelity is controlled via the weight parameter during enhance.
            self.gfpgan = CodeFormer(
                dim_embd=512,
                codebook_size=1024,
                n_head=8,
                n_layers=9,
                connect_list=["32", "64", "128", "256"],
            )
        # initialize face helper
        self.face_helper = FaceRestoreHelper(
            1,
            face_size=512,
            crop_ratio=(1, 1),
            det_model='retinaface_resnet50',
            save_ext='png',
            use_parse=True,
            device=self.device,
            model_rootpath=face_detection_model_path)

        loadnet = torch.load(face_restoration_model_path, map_location='cpu')
        if isinstance(loadnet, dict):
            if 'params_ema' in loadnet:
                state_dict = loadnet['params_ema']
            elif 'params' in loadnet:
                state_dict = loadnet['params']
            elif 'state_dict' in loadnet:
                state_dict = loadnet['state_dict']
            else:
                state_dict = loadnet
        else:
            state_dict = loadnet
        self.gfpgan.load_state_dict(state_dict, strict=True)
        self.gfpgan.eval()
        self.gfpgan = self.gfpgan.to(self.device)

    @torch.no_grad()
    def enhance(self, img, weight=0.5, detection_size=1560, max_faces=32):
        self.face_helper.clean_all()

        original_img = img.copy()
        h_orig, w_orig, _ = original_img.shape

        # ------------------- MODIFICATION FOR DETECTION SIZING -------------------
        # Calculate the scale factor to resize the image for detection
        detection_img = original_img
        scale = 1.0
        if detection_size is not None and detection_size > 0:
            max_dim = max(h_orig, w_orig)
            if max_dim > detection_size:
                scale = detection_size / max_dim
                h_det, w_det = int(round(h_orig * scale)), int(round(w_orig * scale))
                detection_img = cv2.resize(original_img, (w_det, h_det), interpolation=cv2.INTER_AREA)

        # Perform detection on the resized image
        self.face_helper.read_image(detection_img)
        num_faces = self.face_helper.get_face_landmarks_5(max_faces=max_faces, eye_dist_threshold=15)

        # Scale the landmarks and bounding boxes back to the original image's coordinates
        if scale != 1.0:
            for i in range(len(self.face_helper.det_faces)):
                self.face_helper.det_faces[i][:4] /= scale
            for i in range(len(self.face_helper.all_landmarks_5)):
                self.face_helper.all_landmarks_5[i] /= scale

        # Set the helper to use the original, full-resolution image for subsequent steps
        self.face_helper.input_img = original_img
        # --------------------------------------------------------------------------

        # No detected faces: return the untouched image and an empty mask so downstream
        # consumers can safely bypass restoration.
        if num_faces == 0:
            empty_mask = np.zeros((h_orig, w_orig), dtype=np.uint8)
            return original_img, empty_mask

        # align and warp each face
        self.face_helper.align_warp_face()

        if self.device.type == 'cuda' and self.use_half:
            autocast_ctx = torch.autocast(device_type='cuda', dtype=torch.float16)
        else:
            autocast_ctx = nullcontext()

        # face restoration
        if self.model_arch == 'codeformer':
            # CodeFormer expects fidelity w in [0, 1]; clamp to avoid unexpected values.
            weight = float(np.clip(weight, 0.0, 1.0))

        restorer_name = 'CodeFormer' if self.model_arch == 'codeformer' else 'GFPGAN'

        for cropped_face in self.face_helper.cropped_faces:
            # prepare data
            cropped_face_t = img2tensor(cropped_face / 255., bgr2rgb=True, float32=True)
            normalize(cropped_face_t, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), inplace=True)
            cropped_face_t = cropped_face_t.unsqueeze(0).to(self.device)

            try:
                with autocast_ctx:
                    if self.model_arch == 'codeformer':
                        output = self.gfpgan(cropped_face_t, w=weight)[0]
                        restored_face = tensor2img(output, rgb2bgr=True, min_max=(-1, 1))
                    else:
                        output = self.gfpgan(cropped_face_t, return_rgb=False, weight=weight)[0]
                        # convert to image
                        restored_face = tensor2img(output.squeeze(0).float(), rgb2bgr=True, min_max=(-1, 1))
            except RuntimeError as error:
                print(f'\tFailed inference for {restorer_name}: {error}.')
                restored_face = cropped_face

            restored_face = restored_face.astype('uint8')
            self.face_helper.add_restored_face(restored_face)

        self.face_helper.get_inverse_affine()
        
        restored_img = self.face_helper.paste_faces_to_input_image()
        
        h, w, _ = restored_img.shape
        final_soft_mask = np.zeros((h, w), dtype=np.float32)

        if self.face_helper.use_parse:
            if not self.face_helper.soft_masks:
                warnings.warn('soft_masks list is empty. Returning an empty pasting_mask.')
            else:
                for soft_mask in self.face_helper.soft_masks:
                    if soft_mask.ndim == 3 and soft_mask.shape[2] == 1:
                        soft_mask = np.squeeze(soft_mask, axis=2)

                    if soft_mask.shape != (h, w):
                        warnings.warn(f'Soft mask shape {soft_mask.shape} does not match image shape {(h, w)}. Resizing mask.')
                        soft_mask = cv2.resize(soft_mask, (w, h))

                    final_soft_mask = np.maximum(final_soft_mask, soft_mask)

        pasting_mask = (final_soft_mask * 255).astype(np.uint8)

        return restored_img, pasting_mask
