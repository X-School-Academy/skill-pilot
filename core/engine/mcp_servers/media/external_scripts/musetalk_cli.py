#!/home/ubuntu/miniconda3/envs/MuseTalk/bin/python
import contextlib
import logging
import os
import time
import pdb
import re
import numpy as np
import sys
import subprocess
import json
import uuid

from huggingface_hub import snapshot_download
import requests

import argparse
import os
from omegaconf import OmegaConf
import numpy as np
import cv2
import torch
import glob
import pickle
from tqdm import tqdm
import copy
from argparse import Namespace
import shutil
import gdown
import imageio
import ffmpeg
from moviepy.editor import *
from transformers import WhisperModel
import queue
import threading


ProjectDir = os.path.abspath(os.path.dirname(__file__))
CheckpointsDir = os.path.join(ProjectDir, "models")

COMFYUI_INSTALL_PATH = str(os.environ.get("COMFYUI_INSTALL_PATH") or "").strip()
DEFAULT_TMP_ROOT = f"{COMFYUI_INSTALL_PATH}/temp" if COMFYUI_INSTALL_PATH else "/tmp"
DEFAULT_OUTPUT_DIR = f"{COMFYUI_INSTALL_PATH}/output" if COMFYUI_INSTALL_PATH else "/tmp"
DEFAULT_LOG_PATH = f"{DEFAULT_TMP_ROOT}/musetalk.log"


def _configure_logging() -> None:
    log_path = os.environ.get("MUSETALK_LOG_PATH", DEFAULT_LOG_PATH)
    log_level_name = os.environ.get("MUSETALK_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(process)d:%(threadName)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)

    logging.captureWarnings(True)
    root_logger.info("Logging initialized: path=%s level=%s", log_path, log_level_name)


@contextlib.contextmanager
def _log_step(step_name: str, **fields):
    step_logger = logging.getLogger("musetalk_cli")
    start = time.monotonic()
    if fields:
        step_logger.info("START %s %s", step_name, " ".join(f"{k}={v}" for k, v in fields.items()))
    else:
        step_logger.info("START %s", step_name)
    try:
        yield
    finally:
        elapsed_s = time.monotonic() - start
        step_logger.info("END %s elapsed_s=%.3f", step_name, elapsed_s)


_configure_logging()
logger = logging.getLogger("musetalk_cli")

def _gpu_mem_log(prefix: str) -> None:
    if not torch.cuda.is_available():
        return
    try:
        allocated = torch.cuda.memory_allocated() / (1024 ** 3)
        reserved = torch.cuda.memory_reserved() / (1024 ** 3)
        max_allocated = torch.cuda.max_memory_allocated() / (1024 ** 3)
        logger.info(
            "%s cuda_mem_gb allocated=%.3f reserved=%.3f max_allocated=%.3f",
            prefix,
            allocated,
            reserved,
            max_allocated,
        )
    except Exception as e:
        logger.warning("Failed to read CUDA memory stats: %s", e)


def _to_cpu_uint8_frame(frame):
    if isinstance(frame, torch.Tensor):
        frame = frame.detach()
        if frame.is_cuda:
            frame = frame.to("cpu")
        if frame.dtype != torch.uint8:
            frame = frame.clamp(0, 255).to(torch.uint8)
        return frame.numpy()

    if not isinstance(frame, np.ndarray):
        frame = np.asarray(frame)
    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)
    return frame


@torch.no_grad()
def debug_inpainting(video_path, bbox_shift, extra_margin=10, parsing_mode="jaw",
left_cheek_width=90, right_cheek_width=90, cleanup_temp_files=True):
    """Debug inpainting parameters, only process the first frame"""
    # Set default parameters
    args_dict = {
        "result_dir": './results/debug',
        "fps": 25,
        "batch_size": 1,
        "output_vid_name": '',
        "use_saved_coord": False,
        "audio_padding_length_left": 2,
        "audio_padding_length_right": 2,
        "version": "v15",
        "extra_margin": extra_margin,
        "parsing_mode": parsing_mode,
        "left_cheek_width": left_cheek_width,
        "right_cheek_width": right_cheek_width
    }
    args = Namespace(**args_dict)

    # Create debug directory
    os.makedirs(args.result_dir, exist_ok=True)
    # Read first frame
    if get_file_type(video_path) == "video":
        reader = imageio.get_reader(video_path)
        first_frame = reader.get_data(0)
        reader.close()
    else:
        first_frame = cv2.imread(video_path)
        first_frame = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
    # Save first frame
    debug_frame_path = os.path.join(args.result_dir, "debug_frame.png")
    cv2.imwrite(debug_frame_path, cv2.cvtColor(first_frame, cv2.COLOR_RGB2BGR))
    # Get face coordinates
    coord_list, frame_list = get_landmark_and_bbox([debug_frame_path], bbox_shift)
    bbox = coord_list[0]
    frame = frame_list[0]
    if bbox == coord_placeholder:
        return None, "No face detected, please adjust bbox_shift parameter"
    # Initialize face parser
    fp = FaceParsing(
        left_cheek_width=args.left_cheek_width,
        right_cheek_width=args.right_cheek_width
    )
    # Process first frame
    x1, y1, x2, y2 = bbox
    y2 = y2 + args.extra_margin
    y2 = min(y2, frame.shape[0])
    crop_frame = frame[y1:y2, x1:x2]
    crop_frame = cv2.resize(crop_frame,(256,256),interpolation = cv2.INTER_LANCZOS4)
    # Generate random audio features
    random_audio = torch.randn(1, 50, 384, device=device, dtype=weight_dtype)
    audio_feature = pe(random_audio)
    # Get latents
    latents = vae.get_latents_for_unet(crop_frame)
    latents = latents.to(dtype=weight_dtype)
    # Generate prediction results
    pred_latents = unet.model(latents, timesteps, encoder_hidden_states=audio_feature).sample
    recon = vae.decode_latents(pred_latents)
    # Inpaint back to original image
    res_frame = recon[0]
    res_frame = cv2.resize(res_frame.astype(np.uint8),(x2-x1,y2-y1))
    combine_frame = get_image(frame, res_frame, [x1, y1, x2, y2], mode=args.parsing_mode, fp=fp)
    # Save results (no need to convert color space again since get_image already returns RGB format)
    debug_result_path = os.path.join(args.result_dir, "debug_result.png")
    cv2.imwrite(debug_result_path, combine_frame)
    # Create information text
    info_text = f"Parameter information:\n" + \
        f"bbox_shift: {bbox_shift}\n" + \
        f"extra_margin: {extra_margin}\n" + \
        f"parsing_mode: {parsing_mode}\n" + \
        f"left_cheek_width: {left_cheek_width}\n" + \
        f"right_cheek_width: {right_cheek_width}\n" + \
        f"Detected face coordinates: [{x1}, {y1}, {x2}, {y2}]"
    print(info_text)
    print(f"Debug result saved to {debug_result_path}")

    # Cleanup temporary files if requested
    if cleanup_temp_files:
        if os.path.exists(args.result_dir):
            shutil.rmtree(args.result_dir)
            print(f"Cleaned up debug directory: {args.result_dir}")

    return cv2.cvtColor(combine_frame, cv2.COLOR_RGB2BGR), info_text


def print_directory_contents(path):
    for child in os.listdir(path):
        child_path = os.path.join(path, child)
        if os.path.isdir(child_path):
            print(child_path)


def download_model():
    # 检查必需的模型文件是否存在
    required_models = [
        ("MuseTalk UNet", f"{CheckpointsDir}/musetalkV15/unet.pth"),
        ("MuseTalk Config", f"{CheckpointsDir}/musetalkV15/musetalk.json"),
        ("SD VAE", f"{CheckpointsDir}/sd-vae/config.json"),
        ("Whisper", f"{CheckpointsDir}/whisper/config.json"),
        ("DWPose", f"{CheckpointsDir}/dwpose/dw-ll_ucoco_384.pth"),
        ("SyncNet", f"{CheckpointsDir}/syncnet/latentsync_syncnet.pt"),
        ("Face Parse", f"{CheckpointsDir}/face-parse-bisent/79999_iter.pth"),
        ("ResNet", f"{CheckpointsDir}/face-parse-bisent/resnet18-5c106cde.pth"),
    ]
    missing_models = []
    for model_name, model_path in required_models:
        if not os.path.exists(model_path):
            missing_models.append((model_name, model_path))
    if missing_models:
        # 全用英文
        print("The following required model files are missing:")
        for model_name, model_path in missing_models:
            print(f"- {model_name}: {model_path}")
        logger.error("Missing model files: %s", missing_models)
        print("\nPlease run the download script to download the missing models:")
        if sys.platform == "win32":
            print("Windows: Run download_weights.bat")
        else:
            print("Linux/Mac: Run ./download_weights.sh")
        sys.exit(1)
    else:
        print("All required model files exist.")
        logger.info("All required model files exist.")



with _log_step("download_model_check", checkpoints_dir=CheckpointsDir):
    download_model()  # for huggingface deployment.


from musetalk.utils.blending import get_image
from musetalk.utils.face_parsing import FaceParsing
from musetalk.utils.audio_processor import AudioProcessor
from musetalk.utils.utils import get_file_type, get_video_fps, datagen, load_all_model
from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs, coord_placeholder, get_bbox_range


def fast_check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True, timeout=10)
        return True
    except Exception as e:
        logger.warning("ffmpeg not available or not callable: %s", e)
        return False


def get_video_fps_ffprobe(video_path):
    """Get video fps using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        fps_str = result.stdout.strip()
        # Parse fraction format like "30000/1001" or "25/1"
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den)
        else:
            fps = float(fps_str)
        return fps
    except Exception as e:
        print(f"Warning: Failed to get fps using ffprobe: {e}")
        return None


def get_video_duration_ffprobe(video_path):
    """Get video duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        duration_str = result.stdout.strip()
        if duration_str and duration_str != 'N/A':
            return float(duration_str)

        # Fallback to format duration
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        duration_str = result.stdout.strip()
        if duration_str and duration_str != 'N/A':
            return float(duration_str)
        return None
    except Exception as e:
        print(f"Warning: Failed to get duration using ffprobe: {e}")
        return None


def process_frames(res_frame_queue, video_num, coord_list_cycle, frame_list_cycle,
                   result_img_save_path, extra_margin, parsing_mode, fp, producer_done, stop_sentinel):
    """Process frames in a separate thread for parallel execution"""
    idx = 0
    while True:
        if idx >= video_num:
            break
        try:
            res_frame = res_frame_queue.get(block=True, timeout=2)
        except queue.Empty:
            if producer_done.is_set():
                logger.warning(
                    "Frame consumer starved: producer_done=true idx=%s expected=%s queue_empty=true",
                    idx,
                    video_num,
                )
                break
            continue

        if res_frame is stop_sentinel:
            logger.info("Received stop sentinel in frame consumer idx=%s expected=%s", idx, video_num)
            break

        bbox = coord_list_cycle[idx % (len(coord_list_cycle))]
        ori_frame = copy.deepcopy(frame_list_cycle[idx % (len(frame_list_cycle))])
        if bbox == coord_placeholder:
            logger.warning("coord_placeholder encountered idx=%s; dropping frame", idx)
            idx += 1
            continue
        x1, y1, x2, y2 = bbox
        y2 = y2 + extra_margin
        y2 = min(y2, ori_frame.shape[0])
        try:
            res_frame = cv2.resize(res_frame.astype(np.uint8), (x2-x1, y2-y1))
        except Exception as e:
            logger.warning("cv2.resize failed idx=%s bbox=%s err=%s", idx, bbox, e)
            idx += 1
            continue

        combine_frame = get_image(ori_frame, res_frame, [x1, y1, x2, y2], mode=parsing_mode, fp=fp)
        cv2.imwrite(f"{result_img_save_path}/{str(idx).zfill(8)}.png", combine_frame)
        idx += 1


@torch.no_grad()
def inference(audio_path, video_path, bbox_shift, extra_margin=10, parsing_mode="jaw",
left_cheek_width=90, right_cheek_width=90, batch_size=20, progress=None, cleanup_temp_files=True):
    # Set default parameters, aligned with inference.py
    args_dict = {
        "result_dir": './results/output',
        "fps": 25,
        "batch_size": batch_size,
        "output_vid_name": '',
        "use_saved_coord": False,
        "audio_padding_length_left": 2,
        "audio_padding_length_right": 2,
        "version": "v15", # Fixed use v15 version
        "extra_margin": extra_margin,
        "parsing_mode": parsing_mode,
        "left_cheek_width": left_cheek_width,
        "right_cheek_width": right_cheek_width
    }
    args = Namespace(**args_dict)

    # Check ffmpeg
    if not fast_check_ffmpeg():
        print("Warning: Unable to find ffmpeg, please ensure ffmpeg is properly installed")

    logger.info(
        "Inference inputs audio_path=%s video_path=%s bbox_shift=%s extra_margin=%s parsing_mode=%s",
        audio_path,
        video_path,
        bbox_shift,
        extra_margin,
        parsing_mode,
    )

    run_uuid = uuid.uuid4().hex
    temp_work_dir = os.path.join(DEFAULT_TMP_ROOT, f"musetalk_{run_uuid}")
    os.makedirs(temp_work_dir, exist_ok=True)
    logger.info("Temp work dir: %s", temp_work_dir)

    result_img_save_path = os.path.join(temp_work_dir, "generated_frames")
    os.makedirs(result_img_save_path, exist_ok=True)
    crop_coord_save_path = os.path.join(temp_work_dir, f"{run_uuid}.pkl")

    if args.output_vid_name == "":
        output_vid_name = os.path.join(DEFAULT_OUTPUT_DIR, f"musetalk_{run_uuid}.mp4")
    else:
        output_vid_name = os.path.join(DEFAULT_OUTPUT_DIR, os.path.basename(args.output_vid_name))
    os.makedirs(os.path.dirname(output_vid_name), exist_ok=True)
    ############################################## extract frames from source video ##############################################
    if get_file_type(video_path) == "video":
        save_dir_full = os.path.join(temp_work_dir, "input_frames")
        os.makedirs(save_dir_full, exist_ok=True)

        # Get video duration and fps
        fps = get_video_fps(video_path)
        duration = get_video_duration_ffprobe(video_path)
        logger.info("Input video fps=%s duration_s=%s", fps, duration)

        # Calculate max frames for 20 seconds
        max_frames = None
        if duration is not None and duration > 20.0:
            max_frames = int(fps * 20)
            print(f"Video duration: {duration:.2f}s, limiting to first 20 seconds ({max_frames} frames)")
            logger.info("Video truncated: duration_s=%.3f max_frames=%s", duration, max_frames)

        with _log_step("extract_frames", max_frames=max_frames):
            # Read video
            reader = imageio.get_reader(video_path)

            # Save images (limit to first 20 seconds if needed)
            for i, im in enumerate(reader):
                if max_frames is not None and i >= max_frames:
                    break
                imageio.imwrite(f"{save_dir_full}/{i:08d}.png", im)
            reader.close()

        input_img_list = sorted(glob.glob(os.path.join(save_dir_full, '*.[jpJP][pnPN]*[gG]')))
    else: # input img folder
        input_img_list = glob.glob(os.path.join(video_path, '*.[jpJP][pnPN]*[gG]'))
        input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
        fps = args.fps
    ############################################## extract audio feature ##############################################
    # Extract audio features
    with _log_step("extract_audio_features", fps=fps):
        whisper_input_features, librosa_length = audio_processor.get_audio_feature(audio_path)
        whisper_chunks = audio_processor.get_whisper_chunk(
            whisper_input_features,
            device,
            weight_dtype,
            whisper,
            librosa_length,
            fps=fps,
            audio_padding_length_left=args.audio_padding_length_left,
            audio_padding_length_right=args.audio_padding_length_right,
        )
    ############################################## preprocess input image ##############################################
    if os.path.exists(crop_coord_save_path) and args.use_saved_coord:
        print("using extracted coordinates")
        with open(crop_coord_save_path,'rb') as f:
            coord_list = pickle.load(f)
        frame_list = read_imgs(input_img_list)
    else:
        print("extracting landmarks...time consuming")
        with _log_step("extract_landmarks_and_bbox", num_images=len(input_img_list), bbox_shift=bbox_shift):
            coord_list, frame_list = get_landmark_and_bbox(input_img_list, bbox_shift)
        with open(crop_coord_save_path, 'wb') as f:
            pickle.dump(coord_list, f)
    bbox_shift_text = get_bbox_range(input_img_list, bbox_shift)
    print(f"BBox Shift Range: {bbox_shift_text}")
    logger.info("BBox Shift Range: %s", bbox_shift_text)
    
    # Initialize face parser
    fp = FaceParsing(
        left_cheek_width=args.left_cheek_width,
        right_cheek_width=args.right_cheek_width
    )
    i = 0
    input_latent_list = []
    with _log_step("encode_input_latents", num_frames=len(frame_list)):
        for bbox, frame in zip(coord_list, frame_list):
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            y2 = y2 + args.extra_margin
            y2 = min(y2, frame.shape[0])
            crop_frame = frame[y1:y2, x1:x2]
            crop_frame = cv2.resize(crop_frame,(256,256),interpolation = cv2.INTER_LANCZOS4)
            latents = vae.get_latents_for_unet(crop_frame)
            input_latent_list.append(latents)
    logger.info(
        "Latents encoded: count=%s (skipped=%s)",
        len(input_latent_list),
        len(frame_list) - len(input_latent_list),
    )

    # to smooth the first and the last frame
    frame_list_cycle = frame_list + frame_list[::-1]
    coord_list_cycle = coord_list + coord_list[::-1]
    input_latent_list_cycle = input_latent_list + input_latent_list[::-1]
    ############################################## inference batch by batch ##############################################
    print("start inference")
    video_num = len(whisper_chunks)
    batch_size = args.batch_size
    gen = datagen(
        whisper_chunks=whisper_chunks,
        vae_encode_latents=input_latent_list_cycle,
        batch_size=batch_size,
        delay_frame=0,
        device=device,
    )

    # Create queue for parallel processing
    # Important: bound the queue to prevent accumulating GPU tensors when the consumer is slower.
    res_frame_queue = queue.Queue(maxsize=max(16, batch_size * 8))
    producer_done = threading.Event()
    stop_sentinel = object()

    # Start frame processing thread
    process_thread = threading.Thread(
        target=process_frames,
        args=(res_frame_queue, video_num, coord_list_cycle, frame_list_cycle,
              result_img_save_path, args.extra_margin, args.parsing_mode, fp, producer_done, stop_sentinel),
        name="frame-consumer",
        daemon=True,
    )
    process_thread.start()

    # Inference loop - frames are processed in parallel by the thread
    start_time = time.time()
    produced_frames = 0
    expected_batches = int(np.ceil(float(video_num) / batch_size))
    with _log_step("model_inference", video_num=video_num, batch_size=batch_size, expected_batches=expected_batches):
        for batch_idx, (whisper_batch, latent_batch) in enumerate(tqdm(gen, total=expected_batches)):
            if batch_idx % 5 == 0:
                logger.info(
                    "Inference progress batch=%s/%s produced_frames=%s",
                    batch_idx,
                    expected_batches,
                    produced_frames,
                )
                _gpu_mem_log(prefix=f"inference_batch_{batch_idx}")
            audio_feature_batch = pe(whisper_batch)
            # Ensure latent_batch is consistent with model weight type
            latent_batch = latent_batch.to(dtype=weight_dtype)
            pred_latents = unet.model(latent_batch, timesteps, encoder_hidden_states=audio_feature_batch).sample
            recon = vae.decode_latents(pred_latents)
            for res_frame in recon:
                # Ensure we do NOT queue GPU tensors; otherwise the queue can grow and OOM over time.
                res_frame_queue.put(_to_cpu_uint8_frame(res_frame))
                produced_frames += 1
                if produced_frames % 100 == 0:
                    logger.info("Produced frames: %s/%s", produced_frames, video_num)
            del audio_feature_batch, latent_batch, pred_latents, recon

    # Wait for processing thread to finish
    producer_done.set()
    res_frame_queue.put(stop_sentinel)
    process_thread.join(timeout=60)
    if process_thread.is_alive():
        logger.error("Frame processing thread did not exit; continuing anyway to avoid freeze.")
    if produced_frames != video_num:
        logger.warning("Frame count mismatch: produced=%s expected=%s", produced_frames, video_num)
    print(f"Total inference and blending time: {time.time() - start_time:.2f}s")
    # Frame rate (model is trained on 25fps)
    fps = 25
    # Output video path
    silent_video_path = os.path.join(temp_work_dir, f"{run_uuid}_silent.mp4")

    # Read images
    def is_valid_image(file):
        pattern = re.compile(r'\d{8}\.png')
        return pattern.match(file)

    images = []
    files = [file for file in os.listdir(result_img_save_path) if is_valid_image(file)]
    files.sort(key=lambda x: int(x.split('.')[0]))

    with _log_step("load_generated_frames", num_files=len(files)):
        for file in files:
            filename = os.path.join(result_img_save_path, file)
            images.append(imageio.imread(filename))

    # Save video
    with _log_step("write_silent_video", output_path=silent_video_path, fps=fps, num_frames=len(images)):
        imageio.mimwrite(silent_video_path, images, 'FFMPEG', fps=fps, codec='libx264', pixelformat='yuv420p')

    # Check if the input_video and audio_path exist
    if not os.path.exists(silent_video_path):
        raise FileNotFoundError(f"Input video file not found: {silent_video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    # Read video
    reader = imageio.get_reader(silent_video_path)
    fps = reader.get_meta_data()['fps'] # Get original video frame rate
    reader.close() # Otherwise, error on win11: PermissionError: [WinError 32] Another program is using this file, process cannot access. : 'temp.mp4'
    # Store frames in list
    frames = images
    print(len(frames))

    # Load the video
    video_clip = VideoFileClip(silent_video_path)

    # Load the audio
    audio_clip = AudioFileClip(audio_path)

    # Set the audio to the video
    video_clip = video_clip.set_audio(audio_clip)

    # Write the output video
    with _log_step("write_final_video", output_path=output_vid_name):
        video_clip.write_videofile(output_vid_name, codec='libx264', audio_codec='aac',fps=25)
    video_clip.close()
    audio_clip.close()

    # Cleanup temporary files if requested
    if cleanup_temp_files:
        if os.path.exists(temp_work_dir):
            shutil.rmtree(temp_work_dir)
            print(f"Cleaned up temp directory: {temp_work_dir}")

    print(f"result is save to {output_vid_name}")
    return output_vid_name,bbox_shift_text


def check_video(video):
    """Check video fps and convert to 25fps if necessary"""
    if not isinstance(video, str):
        return video # in case of none type

    dir_path, file_name = os.path.split(video)

    # Get video fps using ffprobe
    current_fps = get_video_fps_ffprobe(video)

    # If fps detection failed, use imageio as fallback
    if current_fps is None:
        try:
            reader = imageio.get_reader(video)
            current_fps = reader.get_meta_data()['fps']
            reader.close()
        except:
            print("Warning: Could not detect video fps, assuming 25fps")
            current_fps = 25

    print(f"Detected video fps: {current_fps:.2f}")

    # If video is already 25fps, no conversion needed
    if abs(current_fps - 25.0) < 0.1:
        print("Video is already 25fps, no conversion needed")
        return video

    # Need to convert to 25fps
    print(f"Converting video from {current_fps:.2f}fps to 25fps...")
    output_video = os.path.join(DEFAULT_TMP_ROOT, f"musetalk_25fps_{uuid.uuid4().hex}.mp4")

    try:
        # Use ffmpeg for high-quality fps conversion
        cmd = [
            'ffmpeg',
            '-i', video,
            '-r', '25',
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'medium',
            '-pix_fmt', 'yuv420p',
            '-y',  # Overwrite output file
            output_video
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        print(f"Video converted successfully to: {output_video}")
        return output_video
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg conversion failed: {e}")
        logger.error("FFmpeg conversion failed: %s stdout=%s stderr=%s", e, getattr(e, "stdout", None), getattr(e, "stderr", None))
        print("Falling back to imageio conversion...")

        # Fallback to imageio method
        reader = imageio.get_reader(video)
        fps = reader.get_meta_data()['fps']
        frames = [im for im in reader]
        target_fps = 25
        L = len(frames)
        L_target = int(L / fps * target_fps)
        original_t = [x / fps for x in range(1, L+1)]
        t_idx = 0
        target_frames = []
        for target_t in range(1, L_target+1):
            while target_t / target_fps > original_t[t_idx]:
                t_idx += 1
            if t_idx >= L:
                break
            target_frames.append(frames[t_idx])

        imageio.mimwrite(output_video, target_frames, 'FFMPEG', fps=25, codec='libx264', quality=9, pixelformat='yuv420p')
        print(f"Video converted successfully (imageio) to: {output_video}")
        return output_video


# load model weights
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
with _log_step("load_models", device=device):
    vae, unet, pe = load_all_model(
        unet_model_path="./models/musetalkV15/unet.pth",
        vae_type="sd-vae",
        unet_config="./models/musetalkV15/musetalk.json",
        device=device
    )


# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description="MuseTalk: Real-Time High-Fidelity Video Dubbing Tool")

    # Main input/output arguments
    parser.add_argument("--audio", type=str, help="Path to driving audio file (required unless --json-str is provided)")
    parser.add_argument("--video", type=str, help="Path to reference video file (required unless --json-str is provided)")
    parser.add_argument("--output", type=str, help="Output video path (optional)")
    
    # Video processing parameters
    parser.add_argument("--bbox_shift", type=float, default=6, help="BBox shift value in pixels")
    parser.add_argument("--extra_margin", type=int, default=10, help="Extra margin (0-40)")
    parser.add_argument("--parsing_mode", type=str, choices=["jaw", "raw"], default="jaw", help="Parsing mode (jaw or raw)")
    parser.add_argument("--left_cheek_width", type=int, default=90, help="Left cheek width (20-160)")
    parser.add_argument("--right_cheek_width", type=int, default=90, help="Right cheek width (20-160)")
    parser.add_argument("--batch_size", type=int, default=20, help="Inference batch size (higher is faster but uses more GPU memory)")
    
    # Processing options
    parser.add_argument("--no_float16", dest="use_float16", action="store_false", default=True, help="Disable float16 (enabled by default for faster inference)")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode (process only first frame)")
    parser.add_argument("--keep_temp_files", action="store_true", help="Keep temporary files after processing (by default, temp files are cleaned up)")
    
    # FFMPEG path
    parser.add_argument("--ffmpeg_path", type=str, default="/usr/bin",
                        help="Path to ffmpeg executable")

    # JSON input parameter
    parser.add_argument("--json-str", type=str,
                        help="""JSON string input for batch processing.
                        Format: '{"audio_file": "path/to/audio.wav", "video_file": "path/to/video.mp4"}'
                        When provided, --audio and --video arguments are ignored.
                        All paths should be relative to the project root directory, or start with /.
                        Output will be in JSON string wrapped as: 'other logs <output>{"video_file": "path/to/output.mp4", "error": null}/<output>'
                        """)

    return parser.parse_args()


if __name__ == "__main__":
    logger.info("musetalk_cli starting pid=%s argv=%s", os.getpid(), sys.argv)
    # Change to the script's directory to ensure all relative paths work correctly
    # This is critical for model loading and avoiding path issues
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Parse arguments
    args = parse_arguments()

    # Validate that either JSON or regular arguments are provided
    if not args.json_str and (not args.audio or not args.video):
        print("Error: Either --json-str OR both --audio and --video must be provided")
        sys.exit(1)

    # Parse JSON input if provided
    json_mode = False
    if args.json_str:
        json_mode = True
        try:
            json_input = json.loads(args.json_str)
            # Override audio and video arguments with JSON values
            args.audio = json_input.get("audio_file")
            args.video = json_input.get("video_file")
            args.output = json_input.get("output_file") or args.output

            # Validate required fields
            if not args.audio or not args.video:
                error_msg = "JSON input must contain 'audio_file' and 'video_file' fields"
                print(json.dumps({"video_file": "", "error": error_msg}))
                sys.exit(1)

            # Convert paths to absolute paths relative to project root
            if not os.path.isabs(args.audio):
                args.audio = os.path.join(script_dir, args.audio)
            if not os.path.isabs(args.video):
                args.video = os.path.join(script_dir, args.video)
            if args.output and not os.path.isabs(args.output):
                args.output = os.path.join(DEFAULT_OUTPUT_DIR, args.output)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format: {str(e)}"
            print(json.dumps({"video_file": "", "error": error_msg}))
            sys.exit(1)

    # Wrap everything in try-catch for JSON error handling
    try:
        # Set data type
        global weight_dtype
        if args.use_float16:
            # Convert models to half precision for better performance
            pe = pe.half()
            vae.vae = vae.vae.half()
            unet.model = unet.model.half()
            weight_dtype = torch.float16
        else:
            weight_dtype = torch.float32

        # Move models to specified device
        pe = pe.to(device)
        vae.vae = vae.vae.to(device)
        unet.model = unet.model.to(device)

        global timesteps
        timesteps = torch.tensor([0], device=device)

        # Initialize audio processor and Whisper model
        global audio_processor
        audio_processor = AudioProcessor(feature_extractor_path="./models/whisper")
        global whisper
        whisper = WhisperModel.from_pretrained("./models/whisper")
        whisper = whisper.to(device=device, dtype=weight_dtype).eval()
        whisper.requires_grad_(False)
        logger.info("Whisper model loaded dtype=%s device=%s", weight_dtype, device)

        # Check ffmpeg and add to PATH
        if not fast_check_ffmpeg():
            print(f"Adding ffmpeg to PATH: {args.ffmpeg_path}")
            # According to operating system, choose path separator
            path_separator = ';' if sys.platform == 'win32' else ':'
            os.environ["PATH"] = f"{args.ffmpeg_path}{path_separator}{os.environ['PATH']}"
            if not fast_check_ffmpeg():
                print("Warning: Unable to find ffmpeg, please ensure ffmpeg is properly installed")

        # Preprocess video if needed
        with _log_step("preprocess_video", video=args.video):
            processed_video_path = check_video(args.video)

        # Execute based on mode
        if args.debug:
            print("Running in debug mode - processing only the first frame")
            logger.info("Mode=debug")
            debug_result, debug_info = debug_inpainting(
                processed_video_path,
                args.bbox_shift,
                args.extra_margin,
                args.parsing_mode,
                args.left_cheek_width,
                args.right_cheek_width,
                cleanup_temp_files=not args.keep_temp_files
            )
            # In JSON mode, output result
            if json_mode:
                print(json.dumps({"video_file": "", "error": None}))

            # Cleanup preprocessed video if it was created
            if not args.keep_temp_files and processed_video_path != args.video:
                if os.path.exists(processed_video_path):
                    os.remove(processed_video_path)
                    print(f"Cleaned up preprocessed video: {processed_video_path}")
        else:
            print("Running full inference")
            logger.info("Mode=inference")
            output_path = args.output if args.output else None
            if output_path:
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

            result_path, bbox_info = inference(
                args.audio,
                processed_video_path,
                args.bbox_shift,
                args.extra_margin,
                args.parsing_mode,
                args.left_cheek_width,
                args.right_cheek_width,
                args.batch_size,
                cleanup_temp_files=not args.keep_temp_files
            )
            logger.info("Inference finished result_path=%s bbox_info=%s", result_path, bbox_info)

            # If custom output path is specified and different from result_path
            if output_path and output_path != result_path:
                shutil.copy(result_path, output_path)
                print(f"Copied result to: {output_path}")
                final_output = output_path
            else:
                final_output = result_path

            # In JSON mode, output result as JSON
            if json_mode:
                print(f'<output>{json.dumps({"video_file": final_output, "error": None})}</output>')

            # Cleanup preprocessed video if it was created
            if not args.keep_temp_files and processed_video_path != args.video:
                if os.path.exists(processed_video_path):
                    os.remove(processed_video_path)
                    print(f"Cleaned up preprocessed video: {processed_video_path}")

    except Exception as e:
        logger.exception("Unhandled exception: %s", e)
        # In JSON mode, output error as JSON
        if json_mode:
            print(f'<output>{json.dumps({"video_file": "", "error": str(e)})}</output>')
            sys.stdout.flush()
            sys.stderr.flush()
            # Force-exit to avoid hangs when libraries leave non-daemon threads running
            # (SystemExit can be blocked by such threads).
            os._exit(1)
        else:
            raise
