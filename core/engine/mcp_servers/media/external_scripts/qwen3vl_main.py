#!/home/frankhe/data/AUTOMATIC1111/Qwen3VL-GGUF/.venv/bin/python
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import List

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Qwen3VLChatHandler

# ---------------- Model configuration ----------------
# IQ4_NL version has no respone problem in some cases.
#MODEL_PATH = "/home/frankhe/data/system/ai-models/Qwen3-VL-8B-Instruct-IQ4_NL.gguf"

MODEL_PATH = "/home/frankhe/data/system/ai-models/Huihui-Qwen3-VL-8B-Thinking-abliterated-IQ4_NL.gguf"
MMPROJ_PATH = "/home/frankhe/data/system/ai-models/mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf"


# ---------------- Image / video helpers ----------------

def resize_image_to_max_dimension(image, max_size: int = 512):
    """
    Resize image so that the longest side is max_size pixels.
    Maintains aspect ratio.
    """
    import cv2

    height, width = image.shape[:2]
    if height <= max_size and width <= max_size:
        return image

    if height > width:
        new_height = max_size
        new_width = int(width * (max_size / height))
    else:
        new_width = max_size
        new_height = int(height * (max_size / width))

    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)


def guess_mime_type(path: str | os.PathLike) -> str:
    ext = Path(path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/jpeg")  # default to jpeg if unsure


def image_to_base64_data_uri(file_path: str | os.PathLike, max_size: int = 512) -> str:
    """
    Load an image, resize it to max_size on the long side, and return as base64 data URI.
    """
    import cv2

    # Read image
    image = cv2.imread(str(file_path))
    if image is None:
        raise RuntimeError(f"Failed to load image: {file_path}")

    # Resize
    image = resize_image_to_max_dimension(image, max_size)

    # Encode to JPEG
    mime_type = "image/jpeg"  # Always use JPEG after resizing for consistency
    ok, buf = cv2.imencode(".jpg", image)
    if not ok:
        raise RuntimeError(f"Failed to encode image: {file_path}")

    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def video_to_frame_data_uris(
    video_path: str | os.PathLike,
    frame_step: int = 16,
    max_frames: int = -1,
    max_size: int = 512,
) -> List[str]:
    """
    Optimized frame extraction:
      - Calculate which frames to extract upfront
      - Jump directly to those frames using seek
      - Only decode/process the frames we actually need

    frame_step:
        1  -> keep every frame
        N>1 -> keep 1 out of every N frames (0, N, 2N, ...)
    max_frames:
        -1 -> no cap
        >0 -> stop after this many kept frames
    max_size:
        512 -> resize frames to max 512 on long side (default)
    """
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    if frame_step < 1:
        frame_step = 1

    # Get total frame count
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate which frame indices we want to extract
    frame_indices = []
    frame_num = 0
    while frame_num < total_frames:
        if frame_num % frame_step == 0:
            frame_indices.append(frame_num)
            if max_frames > 0 and len(frame_indices) >= max_frames:
                break
        frame_num += 1

    # Extract only the frames we need by seeking directly to them
    data_uris: List[str] = []
    for frame_idx in frame_indices:
        # Seek to specific frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()

        if not ok or frame is None:
            continue

        # Resize and encode
        frame = resize_image_to_max_dimension(frame, max_size)
        ok, buf = cv2.imencode(".jpg", frame)
        if ok:
            b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
            data_uris.append(f"data:image/jpeg;base64,{b64}")

    cap.release()

    if not data_uris:
        raise RuntimeError(f"Failed to extract frames from video: {video_path}")

    return data_uris

# ---------------- Content builders ----------------

def build_content_for_image(image_file: str, prompt: str, max_size: int = 512):
    return [
        {
            "type": "image_url",
            "image_url": {"url": image_to_base64_data_uri(image_file, max_size)},
        },
        {"type": "text", "text": prompt},
    ]


def build_content_for_video(video_file: str, prompt: str, frame_step: int, max_frames: int, max_size: int = 512):
    frame_uris = video_to_frame_data_uris(video_file, frame_step=frame_step, max_frames=max_frames, max_size=max_size)
    print(f"Total frame_uris: {len(frame_uris)}")
    content = [
        {
            "type": "image_url",
            "image_url": {"url": uri},
        }
        for uri in frame_uris
    ]
    content.append(
        {
            "type": "text",
            "text": (
                "These are sampled frames from a video. "
                "Answer based on the whole video: " + prompt
            ),
        }
    )
    return content


# ---------------- LLM runner ----------------
class suppress_stdout_stderr(object):
    """
    A context manager to temporarily suppress stdout and stderr.
    Works by redirecting sys.stdout and sys.stderr to os.devnull.
    """
    def __enter__(self):
        self.outnull_file = open(os.devnull, 'w')
        self.errnull_file = open(os.devnull, 'w')
        self.old_stdout_fileno_undup = sys.stdout.fileno()
        self.old_stderr_fileno_undup = sys.stderr.fileno()
        self.old_stdout_fileno = os.dup(sys.stdout.fileno())
        self.old_stderr_fileno = os.dup(sys.stderr.fileno())
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        os.dup2(self.outnull_file.fileno(), self.old_stdout_fileno_undup)
        os.dup2(self.errnull_file.fileno(), self.old_stderr_fileno_undup)
        sys.stdout = self.outnull_file
        sys.stderr = self.errnull_file
        return self

    def __exit__(self, *_):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        os.dup2(self.old_stdout_fileno, self.old_stdout_fileno_undup)
        os.dup2(self.old_stderr_fileno, self.old_stderr_fileno_undup)
        self.outnull_file.close()
        self.errnull_file.close()

def extract_output_content(text: str) -> str:
    """Extract content between <output> and </output> tags."""
    match = re.search(r'<output>(.*?)</output>', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: if no output tags found, try to extract after </think>
    if '</think>' in text:
        return text.split('</think>', 1)[1].strip()
    # Last resort: return as-is
    return text.strip()


def run(
    model: Llama,
    content,
    system_prompt: str | None = None,
    max_tokens: int = 512,
) -> str:
    if system_prompt is None:
        system_prompt = (
            "You are an AI assistant who perfectly describes and analyzes "
            "images and video frames."
        )

    res = model.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=max_tokens
    )
    return res["choices"][0]["message"]["content"]


# ---------------- CLI ----------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qwen3-VL local CLI (image/video + prompt -> text)."
    )

    parser.add_argument(
        "--json-str",
        help="JSON string input containing all parameters.",
    )

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--image-file",
        "-i",
        help="Path to an image file.",
    )
    group.add_argument(
        "--video-file",
        "-v",
        help="Path to a video file.",
    )

    parser.add_argument(
        "--prompt",
        "-p",
        help="Text prompt / question about the image or video.",
    )

    parser.add_argument(
        "--frame-step",
        type=int,
        default=16,
        help=(
            "Frame step: keep 1 out of every N frames (0,1 => keep all). "
            "Default: 16 (≈ 1/16 of frames)."
        ),
    )

    parser.add_argument(
        "--video-frames",
        type=int,
        default=-1,
        help=(
            "Number of frames to sample from the video. "
            "-1 = use all frames (default)."
        ),
    )

    parser.add_argument(
        "--model-path",
        default=MODEL_PATH,
        help=f"Path to Qwen3-VL GGUF model (default: {MODEL_PATH})",
    )
    parser.add_argument(
        "--mmproj-path",
        default=MMPROJ_PATH,
        help=f"Path to mmproj GGUF file (default: {MMPROJ_PATH})",
    )

    parser.add_argument(
        "--thinking",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="use_think_prompt (for thinking model). Default: True. Use --no-thinking to disable.",
    )

    parser.add_argument(
        "--n-gpu-layers",
        type=int,
        default=-1,
        help="Number of layers to offload to GPU (-1 = all, 0 = CPU only).",
    )

    parser.add_argument(
        "--max-size",
        type=int,
        default=512,
        help="Maximum size (in pixels) for the longest side of images/frames. Default: 512.",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum number of tokens to generate in the response. Default: 512.",
    )

    return parser.parse_args()


def main():
    """
    Main entry point for Qwen3-VL vision model inference.

    Supports two input modes:
    1. CLI arguments (backward compatible)
    2. JSON input via --json-str

    JSON Input Format (--json-str):
        {
            "prompt": "Describe this image",           # Required: text prompt/question
            "image_file": "/path/to/image.jpg",        # Optional: path to image file
            "video_file": "/path/to/video.mp4",        # Optional: path to video file
            "frame_step": 16,                          # Optional: frame sampling step (default: 16)
            "max_frames": -1,                          # Optional: max frames to extract (default: -1 = all)
            "max_size": 512,                           # Optional: max dimension for images/frames (default: 512)
            "max_tokens": 512,                         # Optional: max tokens in response (default: 512)
            "model_path": "/path/to/model.gguf",       # Optional: custom model path
            "mmproj_path": "/path/to/mmproj.gguf",     # Optional: custom mmproj path
            "thinking": true,                          # Optional: enable thinking mode (default: true)
            "n_gpu_layers": -1                         # Optional: GPU layers (default: -1 = all)
        }

    Output format with --json-str:
        <json-output>{"output": "model response text"}</json-output>

    Note: Either image_file or video_file can be provided, not both.
          If neither is provided, text-only mode is used.
    """
    args = parse_args()

    # Parse JSON input if provided
    if args.json_str:
        try:
            data = json.loads(args.json_str)

            # Extract parameters from JSON
            prompt = data.get('prompt')
            if not prompt:
                raise ValueError("JSON input must contain 'prompt' field")

            image_file = data.get('image_file')
            video_file = data.get('video_file')
            frame_step = data.get('frame_step', 16)
            max_frames = data.get('max_frames', -1)
            max_size = data.get('max_size', 512)
            max_tokens = data.get('max_tokens', 512)
            model_path = data.get('model_path', MODEL_PATH)
            mmproj_path = data.get('mmproj_path', MMPROJ_PATH)
            thinking = data.get('thinking', True)
            n_gpu_layers = data.get('n_gpu_layers', -1)

        except json.JSONDecodeError as e:
            error_output = {'error': f'Invalid JSON input: {e}'}
            print(f"<json-output>{json.dumps(error_output)}</json-output>")
            sys.exit(1)
        except ValueError as e:
            error_output = {'error': str(e)}
            print(f"<json-output>{json.dumps(error_output)}</json-output>")
            sys.exit(1)
    else:
        # Use CLI arguments
        if not args.prompt:
            print("ERROR: --prompt is required when not using --json-str", file=sys.stderr)
            sys.exit(1)

        prompt = args.prompt
        image_file = args.image_file
        video_file = args.video_file
        frame_step = args.frame_step
        max_frames = args.video_frames
        max_size = args.max_size
        max_tokens = args.max_tokens
        model_path = args.model_path
        mmproj_path = args.mmproj_path
        thinking = args.thinking
        n_gpu_layers = args.n_gpu_layers

    # Init model (suppress initialization messages but catch errors)
    try:
        with suppress_stdout_stderr():
            llm = Llama(
                model_path=model_path,
                chat_handler=Qwen3VLChatHandler(
                    clip_model_path=mmproj_path,
                    use_think_prompt=thinking,
                    verbose=False
                ),
                n_gpu_layers=n_gpu_layers,
                n_ctx=40 * 1024, # it will OOM for more ctx
                swa_full=True,
                verbose=False,
            )
    except Exception as e:
        error_msg = str(e).lower()

        # Check for specific error types
        if "out of memory" in error_msg or "oom" in error_msg:
            print("ERROR: GPU Out of Memory (OOM)", file=sys.stderr)
            print("Try reducing context size (n_ctx) or use fewer GPU layers (--n-gpu-layers)", file=sys.stderr)
        elif "cuda" in error_msg or "gpu" in error_msg or "device" in error_msg:
            print("ERROR: GPU Device Error", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            print("Try running with --n-gpu-layers 0 to use CPU only", file=sys.stderr)
        elif "failed to load" in error_msg or "cannot open" in error_msg:
            print("ERROR: Failed to load model", file=sys.stderr)
            print(f"Model path: {model_path}", file=sys.stderr)
            print(f"MMProj path: {mmproj_path}", file=sys.stderr)
            print("", file=sys.stderr)
            print("This could be caused by:", file=sys.stderr)
            print("  1. Out of Memory (OOM) - Most common cause", file=sys.stderr)
            print("     → Try: --n-gpu-layers 0 (CPU only)", file=sys.stderr)
            print("     → Or reduce --n-gpu-layers to a smaller number", file=sys.stderr)
            print("  2. Incorrect file path or missing model files", file=sys.stderr)
            print("     → Check if the files exist at the paths above", file=sys.stderr)
            print("  3. Corrupted model file", file=sys.stderr)
            print("     → Try re-downloading the model", file=sys.stderr)
        else:
            print(f"ERROR: Failed to initialize model: {e}", file=sys.stderr)

        if args.json_str:
            error_output = {'error': f'Model initialization failed: {e}'}
            print(f"<json-output>{json.dumps(error_output)}</json-output>")

        sys.exit(1)

    # Build content
    try:
        if image_file:
            content = build_content_for_image(image_file, prompt, max_size)
        elif video_file:
            step = frame_step if frame_step and frame_step > 1 else 1
            content = build_content_for_video(
                video_file,
                prompt,
                frame_step=step,
                max_frames=max_frames,
                max_size=max_size
            )
        else:
            # Text-only prompt
            content = [{"type": "text", "text": prompt}]
    except Exception as e:
        if args.json_str:
            error_output = {'error': f'Content preparation failed: {e}'}
            print(f"<json-output>{json.dumps(error_output)}</json-output>")
        else:
            print(f"ERROR: Content preparation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Run & print output
    try:
        answer = run(llm, content, max_tokens=max_tokens)
        output_content = extract_output_content(answer)

        if args.json_str:
            # JSON output format
            result = {'output': output_content}
            print(f"<json-output>{json.dumps(result)}</json-output>")
        else:
            # Standard output format
            print("<output>")
            print(output_content)
            print("</output>")

        sys.exit(0)
    except Exception as e:
        error_msg = str(e).lower()

        if args.json_str:
            error_output = {'error': f'Inference failed: {e}'}
            print(f"<json-output>{json.dumps(error_output)}</json-output>")
        else:
            if "out of memory" in error_msg or "oom" in error_msg:
                print("ERROR: GPU Out of Memory during inference", file=sys.stderr)
                print("Try using a smaller image/video or reducing context size", file=sys.stderr)
            else:
                print(f"ERROR: Inference failed: {e}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()

