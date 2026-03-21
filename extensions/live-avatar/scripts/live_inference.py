import os
import json
import pickle
import glob
import shutil
import threading
import queue
import time
import logging
import asyncio
import scipy.signal
import torch
import cv2
import numpy as np
from tqdm import tqdm
from types import SimpleNamespace

# Import utility functions from musetalk package
from musetalk.utils.utils import datagen, load_all_model
from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs
from musetalk.utils.blending import get_image_prepare_material
from musetalk.utils.face_parsing import FaceParsing
from musetalk.whisper.audio2feature import Audio2Feature


def get_image_blending(image, face, face_box, mask_array, crop_box):
    """Fast cv2-based blending for real-time use.

    Handles out-of-bounds crop_box coordinates: PIL's crop() pads silently when
    the box extends outside the image, but numpy slicing with negative indices
    treats them as offsets from the end, producing wrong/empty slices.
    We clamp to image bounds and adjust paste offsets accordingly.
    """
    x, y, x1, y1 = face_box
    x_s, y_s, x_e, y_e = crop_box
    h, w = image.shape[:2]

    # Clamp crop region to image boundaries
    cs_y, ce_y = max(0, y_s), min(h, y_e)
    cs_x, ce_x = max(0, x_s), min(w, x_e)
    if cs_y >= ce_y or cs_x >= ce_x:
        return image

    face_large = image[cs_y:ce_y, cs_x:ce_x].copy()
    fl_h, fl_w = face_large.shape[:2]

    # Face paste offsets within face_large (adjusted for clamping)
    dst_y,  dst_y1 = y  - cs_y, y1 - cs_y
    dst_x,  dst_x1 = x  - cs_x, x1 - cs_x

    # Clip paste region and compute corresponding face source offsets
    src_y = max(0, -dst_y)
    src_x = max(0, -dst_x)
    dst_y,  dst_x  = max(0, dst_y),  max(0, dst_x)
    dst_y1, dst_x1 = min(fl_h, dst_y1), min(fl_w, dst_x1)

    if dst_y < dst_y1 and dst_x < dst_x1:
        face_large[dst_y:dst_y1, dst_x:dst_x1] = \
            face[src_y:src_y + (dst_y1 - dst_y), src_x:src_x + (dst_x1 - dst_x)]

    # Crop mask to match the clamped face_large region
    m_y0, m_x0 = cs_y - y_s, cs_x - x_s
    if len(mask_array.shape) == 2:
        mask_image = mask_array
    else:
        mask_image = cv2.cvtColor(mask_array, cv2.COLOR_BGR2GRAY)
    mask_crop = (mask_image[m_y0:m_y0 + fl_h, m_x0:m_x0 + fl_w] / 255).astype(np.float32)

    if mask_crop.shape[:2] == (fl_h, fl_w):
        image[cs_y:ce_y, cs_x:ce_x] = cv2.blendLinear(
            face_large, image[cs_y:ce_y, cs_x:ce_x], mask_crop, 1 - mask_crop
        )
    else:
        image[cs_y:ce_y, cs_x:ce_x] = face_large  # fallback: paste without blending

    return image

import scripts.openai_live as openai_live
from scripts.openai_live import generated_frame_queue, first_frame_event, turn_sequence, END_OF_VIDEO

# Global avatar instance and main event loop reference
avatar = None
running_loop = None

def setup_logging(log_file="/var/log/gpu_app_worker.log"):
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode='a')
        ]
    )

# Load model weights
audio_processor = Audio2Feature(model_path="./models/whisper/tiny.pt")
vae, unet, pe = load_all_model()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
timesteps = torch.tensor([0], device=device)
pe = pe.half().to(device)
vae.vae = vae.vae.half().to(device)
unet.model = unet.model.half().to(device)
fp = FaceParsing()


def video2imgs(vid_path, save_path, ext='.png', cut_frame=10000000):
    cap = cv2.VideoCapture(vid_path)
    count = 0
    while True:
        if count > cut_frame:
            break
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"{save_path}/{count:08d}.{ext}", frame)
            count += 1
        else:
            break
    cap.release()


def osmakedirs(path_list):
    for path in path_list:
        os.makedirs(path, exist_ok=True)


@torch.no_grad()
def warm_up(batch_size=16):
    logging.info('warmup model...')
    whisper_batch = np.ones((batch_size, 50, 384), dtype=np.float32)
    latent_batch = torch.ones(batch_size, 8, 32, 32).to(device)

    audio_feature_batch = torch.from_numpy(whisper_batch)
    audio_feature_batch = audio_feature_batch.to(device=device, dtype=unet.model.dtype)
    audio_feature_batch = pe(audio_feature_batch)
    latent_batch = latent_batch.to(dtype=unet.model.dtype)
    pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
    pred_latents = pred_latents.to(device=device, dtype=vae.vae.dtype)
    vae.decode_latents(pred_latents)


@torch.no_grad()
class Avatar:
    def __init__(self, avatar_id, video_path, bbox_shift, batch_size, preparation):
        self.avatar_id = avatar_id
        self.video_path = video_path
        self.bbox_shift = bbox_shift
        self.avatar_path = f"./results/avatars/{avatar_id}"
        self.full_imgs_path = f"{self.avatar_path}/full_imgs"
        self.coords_path = f"{self.avatar_path}/coords.pkl"
        self.latents_out_path = f"{self.avatar_path}/latents.pt"
        self.mask_out_path = f"{self.avatar_path}/mask"
        self.mask_coords_path = f"{self.avatar_path}/mask_coords.pkl"
        self.avatar_info_path = f"{self.avatar_path}/avatar_info.json"
        self.avatar_info = {
            "avatar_id": avatar_id,
            "video_path": video_path,
            "bbox_shift": bbox_shift
        }
        self.preparation = preparation
        self.batch_size = batch_size
        self.idx = 0
        self.init()

    def init(self):
        if self.preparation:
            if os.path.exists(self.avatar_path):
                logging.info(f"{self.avatar_id} already exists, reusing it.")
                self.input_latent_list_cycle = torch.load(self.latents_out_path)
                with open(self.coords_path, 'rb') as f:
                    self.coord_list_cycle = pickle.load(f)
                input_img_list = sorted(
                    glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]')),
                    key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
                )
                self.frame_list_cycle = read_imgs(input_img_list)
                with open(self.mask_coords_path, 'rb') as f:
                    self.mask_coords_list_cycle = pickle.load(f)
                input_mask_list = sorted(
                    glob.glob(os.path.join(self.mask_out_path, '*.[jpJP][pnPN]*[gG]')),
                    key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
                )
                self.mask_list_cycle = read_imgs(input_mask_list)
            else:
                logging.info("Creating avatar: %s", self.avatar_id)
                osmakedirs([self.avatar_path, self.full_imgs_path, self.mask_out_path])
                self.prepare_material()
        else:
            if not os.path.exists(self.avatar_path):
                logging.error(f"{self.avatar_id} does not exist, set preparation to True")
                exit(1)
            with open(self.avatar_info_path, "r") as f:
                avatar_info = json.load(f)
            if avatar_info['bbox_shift'] != self.avatar_info['bbox_shift']:
                logging.error("【bbox_shift】 is changed, you need to re-create it!")
                exit(1)
            else:
                self.input_latent_list_cycle = torch.load(self.latents_out_path)
                with open(self.coords_path, 'rb') as f:
                    self.coord_list_cycle = pickle.load(f)
                input_img_list = sorted(
                    glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]')),
                    key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
                )
                self.frame_list_cycle = read_imgs(input_img_list)
                with open(self.mask_coords_path, 'rb') as f:
                    self.mask_coords_list_cycle = pickle.load(f)
                input_mask_list = sorted(
                    glob.glob(os.path.join(self.mask_out_path, '*.[jpJP][pnPN]*[gG]')),
                    key=lambda x: int(os.path.splitext(os.path.basename(x))[0])
                )
                self.mask_list_cycle = read_imgs(input_mask_list)

    def prepare_material(self):
        logging.info("Preparing data materials...")
        with open(self.avatar_info_path, "w") as f:
            json.dump(self.avatar_info, f)

        if os.path.isfile(self.video_path):
            video2imgs(self.video_path, self.full_imgs_path, ext='png')
        else:
            logging.info(f"Copying files from {self.video_path}")
            files = sorted([file for file in os.listdir(self.video_path) if file.endswith("png")])
            for filename in files:
                shutil.copyfile(
                    os.path.join(self.video_path, filename),
                    os.path.join(self.full_imgs_path, filename)
                )
        input_img_list = sorted(glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]')))

        logging.info("Extracting landmarks...")
        coord_list, frame_list = get_landmark_and_bbox(input_img_list, self.bbox_shift)
        input_latent_list = []
        idx = -1
        coord_placeholder_val = (0.0, 0.0, 0.0, 0.0)
        for bbox, frame in zip(coord_list, frame_list):
            idx += 1
            if bbox == coord_placeholder_val:
                continue
            x1, y1, x2, y2 = bbox
            crop_frame = frame[y1:y2, x1:x2]
            resized_crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            latents = vae.get_latents_for_unet(resized_crop_frame)
            input_latent_list.append(latents)

        self.frame_list_cycle = frame_list + frame_list[::-1]
        self.coord_list_cycle = coord_list + coord_list[::-1]
        self.input_latent_list_cycle = input_latent_list + input_latent_list[::-1]
        self.mask_coords_list_cycle = []
        self.mask_list_cycle = []

        for i, frame in enumerate(self.frame_list_cycle):
            cv2.imwrite(f"{self.full_imgs_path}/{str(i).zfill(8)}.png", frame)
            face_box = self.coord_list_cycle[i]
            mask, crop_box = get_image_prepare_material(frame, face_box, fp=fp)
            cv2.imwrite(f"{self.mask_out_path}/{str(i).zfill(8)}.png", mask)
            self.mask_coords_list_cycle.append(crop_box)
            self.mask_list_cycle.append(mask)

        with open(self.mask_coords_path, 'wb') as f:
            pickle.dump(self.mask_coords_list_cycle, f)

        with open(self.coords_path, 'wb') as f:
            pickle.dump(self.coord_list_cycle, f)

        torch.save(self.input_latent_list_cycle, self.latents_out_path)

    def process_frames(self, res_frame_queue, video_len, end_idx, frame_duration, current_turn_sequence):
        logging.info(f"Processing %d frames, frame_duration {frame_duration}...", video_len)
        while self.idx < end_idx:
            try:
                res_frame = res_frame_queue.get(timeout=1)
            except queue.Empty:
                continue
            bbox = self.coord_list_cycle[self.idx % len(self.coord_list_cycle)]
            ori_frame = self.frame_list_cycle[self.idx % len(self.frame_list_cycle)].copy()
            x1, y1, x2, y2 = bbox
            try:
                res_frame = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2 - y1))
            except Exception as e:
                logging.error("Error resizing frame: %s", e)
                continue
            mask = self.mask_list_cycle[self.idx % len(self.mask_list_cycle)]
            mask_crop_box = self.mask_coords_list_cycle[self.idx % len(self.mask_coords_list_cycle)]
            combine_frame = get_image_blending(ori_frame, res_frame, bbox, mask, mask_crop_box)

            # Safely put the frame into the async queue from a different thread
            async def put_frame(frame, frame_duration):
                if current_turn_sequence == turn_sequence.value:
                    if not turn_sequence.playing:
                        turn_sequence.playing = True
                    await generated_frame_queue.put(SimpleNamespace(frame=frame, duration=frame_duration))
            asyncio.run_coroutine_threadsafe(put_frame(combine_frame, frame_duration), running_loop)

            if not first_frame_event.is_set():
                first_frame_event.set()
            self.idx += 1

    def inference(self, audio_data, fps, current_turn_sequence, total_time):
        if audio_data is None:
            logging.info("Ending inference, add an END_OF_VIDEO flag")
            asyncio.run_coroutine_threadsafe(
                generated_frame_queue.put(SimpleNamespace(frame=END_OF_VIDEO, duration=0)), running_loop
            )
            return
        else:
            logging.info(f"Starting inference: turn seq {current_turn_sequence}, total video time {total_time}s")

        start_time = time.time()
        whisper_feature = audio_processor.audio2feat(audio_data)
        whisper_chunks = audio_processor.feature2chunks(feature_array=whisper_feature, fps=fps)
        video_num = len(whisper_chunks)
        frame_duration = total_time / video_num
        res_frame_queue = queue.Queue()
        end_idx = self.idx + video_num
        process_thread = threading.Thread(
            target=self.process_frames,
            args=(res_frame_queue, video_num, end_idx, frame_duration, current_turn_sequence)
        )
        process_thread.start()

        # Convert numpy chunks from old whisper to tensors for new datagen
        whisper_chunks_tensors = [torch.from_numpy(chunk) for chunk in whisper_chunks]
        gen = datagen(whisper_chunks_tensors, self.input_latent_list_cycle, self.batch_size)
        for _, (whisper_batch, latent_batch) in enumerate(
            tqdm(gen, total=int(np.ceil(float(video_num) / self.batch_size)))
        ):
            audio_feature_batch = whisper_batch.to(device=device, dtype=unet.model.dtype)
            audio_feature_batch = pe(audio_feature_batch)
            latent_batch = latent_batch.to(device=device, dtype=unet.model.dtype)
            pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
            pred_latents = pred_latents.to(device=device, dtype=vae.vae.dtype)
            recon = vae.decode_latents(pred_latents)
            for res_frame in recon:
                res_frame_queue.put(res_frame)

        process_thread.join()
        logging.info(f"Processing video took %.2fms, turn seq {current_turn_sequence}", (time.time() - start_time) * 1000)


def downsample(audio, orig_sr=24000, target_sr=16000):
    new_length = int(len(audio) * target_sr / orig_sr)
    return scipy.signal.resample(audio, new_length).astype(audio.dtype)


def init_live_inference(avatar_video_file='data/video/ryan.mp4'):
    global avatar
    setup_logging()
    bbox_shift = 0
    batch_size = 4
    avatar_id = os.path.splitext(os.path.basename(avatar_video_file))[0]
    avatar_folder = f"./results/avatars/{avatar_id}"
    preparation = not os.path.exists(avatar_folder)
    avatar = Avatar(
        avatar_id=avatar_id,
        video_path=avatar_video_file,
        bbox_shift=bbox_shift,
        batch_size=batch_size,
        preparation=preparation
    )
    warm_up(batch_size)


# Define a global lock for inference, make sure inference one by one
inference_lock = threading.Lock()


def safe_inference(audio_data, fps, current_turn_sequence, total_time):
    with inference_lock:
        avatar.inference(audio_data, fps, current_turn_sequence, total_time)


async def start_live_inference(video_fps=25, audio_buffer_time=3):
    global running_loop
    running_loop = asyncio.get_running_loop()
    total_time = 0
    while True:
        # Buffer at least audio_buffer_time seconds of audio (s × 24000 samples/s × 2 bytes/sample)
        required_bytes = audio_buffer_time * 24000 * 2
        buffered_audio = bytearray()
        send_end_tensor = False
        logging.info("Buffering audio for 3 seconds…")
        while len(buffered_audio) < required_bytes:
            audio_chunk = await openai_live.get_audio()
            if audio_chunk is None:
                send_end_tensor = True
                break
            buffered_audio.extend(audio_chunk)

        if len(buffered_audio) == 0:
            if send_end_tensor:
                await asyncio.to_thread(safe_inference, None, video_fps, turn_sequence.value, 0)
                send_end_tensor = False
            continue

        duration = len(buffered_audio) / 2 / 24000
        total_time += duration
        audio_np = np.frombuffer(buffered_audio, dtype=np.int16)
        downsampled_audio = downsample(audio_np, orig_sr=24000, target_sr=16000)

        # Create a tensor from the raw bytes
        audio_tensor = torch.frombuffer(downsampled_audio, dtype=torch.int16)
        # Convert to float and normalize
        audio_tensor = audio_tensor.float() / 32768.0

        await asyncio.to_thread(safe_inference, audio_tensor, video_fps, turn_sequence.value, duration)

        if send_end_tensor:
            logging.warning(f"Buffering audio for a turn, total audio time: {total_time}")
            await asyncio.to_thread(safe_inference, None, video_fps, turn_sequence.value, 0)
            send_end_tensor = False
