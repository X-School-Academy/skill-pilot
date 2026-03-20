#!/home/ubuntu/miniconda3/envs/SongBloom/bin/python
import os
import sys
import torch
import torchaudio
import argparse
import json
import uuid
from pathlib import Path
from omegaconf import OmegaConf, DictConfig

# Get the script's directory to make it runnable from any location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR  # Assuming script is in project root

# Hardcode environment variables from set_env.sh
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['NLTK_DATA'] = os.path.join(PROJECT_ROOT, 'SongBloom/g2p/cn_zh_g2p/nltk_data')
os.environ['PYTHONPATH'] = PROJECT_ROOT + ':' + os.environ.get('PYTHONPATH', '')
os.environ['DISABLE_FLASH_ATTN'] = '1'

from SongBloom.models.songbloom.songbloom_pl import SongBloom_Sampler
from normalize_lyrics import clean_lyrics

COMFYUI_INSTALL_PATH = str(os.environ.get("COMFYUI_INSTALL_PATH") or "").strip()
DEFAULT_OUTPUT_DIR = f"{COMFYUI_INSTALL_PATH}/output" if COMFYUI_INSTALL_PATH else "/tmp"

def load_config(cfg_file, parent_dir="./") -> DictConfig:
    OmegaConf.register_new_resolver("eval", lambda x: eval(x))
    OmegaConf.register_new_resolver("concat", lambda *x: [xxx for xx in x for xxx in xx])
    OmegaConf.register_new_resolver("get_fname", lambda x: os.path.splitext(os.path.basename(x))[0])
    OmegaConf.register_new_resolver("load_yaml", lambda x: OmegaConf.load(x))
    OmegaConf.register_new_resolver("dynamic_path", lambda x: x.replace("???", parent_dir))

    file_cfg = OmegaConf.load(open(cfg_file, 'r')) if cfg_file is not None else OmegaConf.create()

    return file_cfg


def process_audio(audio_path, target_sr=48000, target_duration=10.0, dtype=torch.float16):
    """
    Load audio, resample to target sample rate, convert to mono, and trim to target duration.
    """
    # Load audio
    wav, sr = torchaudio.load(audio_path)

    # Resample if necessary
    if sr != target_sr:
        print(f"Resampling audio from {sr}Hz to {target_sr}Hz")
        wav = torchaudio.functional.resample(wav, sr, target_sr)

    # Convert to mono by averaging channels
    wav = wav.mean(dim=0, keepdim=True).to(dtype)

    # Trim to target duration
    max_samples = int(target_duration * target_sr)
    wav = wav[..., :max_samples]

    print(f"Audio processed: {wav.shape[1] / target_sr:.2f} seconds, {target_sr}Hz")

    return wav


def apply_fade_out(
    wav: torch.Tensor,
    sample_rate: int,
    fade_duration: float = 6.0,
    fade_power: float = 2.0,
) -> torch.Tensor:
    """Apply a power-based fade-out over the last ``fade_duration`` seconds."""
    fade_samples = int(fade_duration * sample_rate)
    if fade_samples <= 0:
        return wav

    fade_samples = min(fade_samples, wav.shape[-1])
    power = max(fade_power, 0.0) if fade_power is not None else 1.0
    fade_curve = torch.linspace(1.0, 0.0, fade_samples, device=wav.device, dtype=wav.dtype) ** power
    wav[..., -fade_samples:] = wav[..., -fade_samples:] * fade_curve
    return wav


def main():
    parser = argparse.ArgumentParser(description='Generate songs from lyrics and reference voice')
    parser.add_argument('--json-str', type=str, required=True, help='JSON string with lyrics and ref_voice')
    parser.add_argument('--model-name', type=str, default='songbloom_full_150s')
    parser.add_argument('--local-dir', type=str, default=os.path.join(PROJECT_ROOT, 'cache'))
    parser.add_argument('--output-dir', type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--dtype', type=str, default='float16', choices=['float32', 'bfloat16', 'float16'])
    parser.add_argument('--device', type=str, default='cuda:0')
    parser.add_argument('--fade-duration', type=float, default=6.0, help='Fade-out duration in seconds')
    args = parser.parse_args()

    try:
        # Parse input JSON
        input_data = json.loads(args.json_str)
        lyrics = input_data.get('text') or input_data.get('lyrics')
        lyrics = clean_lyrics(lyrics)
        ref_voice = input_data.get('ref_voice')
        output_dir = str(input_data.get('output_dir') or args.output_dir)

        if not lyrics or not ref_voice:
            raise ValueError("Input JSON must contain 'lyrics' and 'ref_voice' fields")

        print(f"Processing song generation...")
        print(f"Lyrics length: {len(lyrics)} characters")
        print(f"Reference voice: {ref_voice}")

        # Check if ref_voice file exists
        if not os.path.exists(ref_voice):
            raise FileNotFoundError(f"Reference voice file not found: {ref_voice}")

        # Load config
        print("Loading model configuration...")
        cfg = load_config(f"{args.local_dir}/{args.model_name}.yaml", parent_dir=args.local_dir)
        cfg.max_dur = cfg.max_dur + 10

        # Setup device and dtype
        dtype = getattr(torch, args.dtype)
        device = torch.device(args.device)

        # Load model
        print(f"Loading model on {device} with {args.dtype} precision...")
        model = SongBloom_Sampler.build_from_trainer(cfg, strict=False, dtype=dtype, device=device)
        model.set_generation_params(**cfg.inference)

        # Process reference voice audio (trim to 10s, convert to 48kHz)
        print("Processing reference voice audio...")
        prompt_wav = process_audio(ref_voice, target_sr=model.sample_rate, target_duration=10.0, dtype=dtype)

        # Generate audio
        print("Generating audio...")
        wav = model.generate(lyrics, prompt_wav)
        wav = apply_fade_out(wav, model.sample_rate, fade_duration=args.fade_duration)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Generate UUID filename
        audio_uuid = str(uuid.uuid4())
        audio_file = os.path.join(output_dir, f"{audio_uuid}.wav")

        # Save audio file
        print(f"Saving audio to: {audio_file}")
        torchaudio.save(audio_file, wav[0].cpu().float(), model.sample_rate)

        # Prepare output JSON
        output_data = {
            'audio_file': audio_file
        }

        # Print output in the specified format
        print(f"<json-output>{json.dumps(output_data)}</json-output>")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        # Output error in JSON format
        error_output = {
            'error': str(e),
            'audio_file': None
        }
        print(f"<json-output>{json.dumps(error_output)}</json-output>")
        sys.exit(1)


if __name__ == "__main__":
    main()
