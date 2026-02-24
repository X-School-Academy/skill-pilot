import subprocess
import os
import json
import torch
import numpy as np
from PIL import Image
import folder_paths

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_typ = AnyType("*")

class CommandExecNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "command": ("STRING", {
                    "multiline": True,
                    "default": "echo {input}"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff
                }),
            },
            "optional": {
                "input": (any_typ,),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "run_command"
    CATEGORY = "Custom/Utility"

    @classmethod
    def IS_CHANGED(cls, command, seed, input=None):
        # Create a hash of inputs to detect changes
        import hashlib

        # Hash the command and seed
        hash_input = f"{command}_{seed}"

        # Handle different input types
        if input is not None:
            if isinstance(input, torch.Tensor):
                # For tensors, use shape and a sample of values
                hash_input += f"_tensor_{input.shape}_{input.sum().item()}"
            else:
                # For other types, convert to string
                hash_input += f"_{str(input)}"

        # Return hash - when inputs change, hash changes, node re-runs
        return hashlib.md5(hash_input.encode()).hexdigest()

    def run_command(self, command, seed, input=None):
        import subprocess

        # Process input - if image, save to temp file; if string, use as-is
        input_value = ""

        if input is None:
            # No input provided, leave input_value as empty string
            input_value = ""
        elif isinstance(input, torch.Tensor):
            # Handle image tensor - save to ComfyUI temp folder
            temp_dir = folder_paths.get_temp_directory()
            temp_filename = f"terminal_input_{os.getpid()}_{id(input)}.png"
            temp_path = os.path.join(temp_dir, temp_filename)

            # Convert tensor to PIL Image and save
            # Assuming input shape is [B, H, W, C] or [H, W, C]
            img_np = input.cpu().numpy()
            if img_np.ndim == 4:
                img_np = img_np[0]  # Take first image from batch

            # Convert to 0-255 range if needed
            if img_np.max() <= 1.0:
                img_np = (img_np * 255).astype(np.uint8)
            else:
                img_np = img_np.astype(np.uint8)

            img = Image.fromarray(img_np)
            img.save(temp_path)
            input_value = temp_path

        elif isinstance(input, str):
            # If input is already a string, use it directly
            input_value = input
        else:
            # Try to convert to string
            input_value = str(input)

        # Replace {input} placeholder in command
        processed_command = command.replace("{input}", input_value)

        try:
            result = subprocess.check_output(
                processed_command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True
            )
        except subprocess.CalledProcessError as e:
            result = f"[ERROR] Code {e.returncode}:\n{e.output}"

        return (result,)


class CommandExecJsonNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "executable": ("STRING", {
                    "multiline": False,
                    "default": "/path/to/script.py"
                }),
                "json_input": ("STRING", {
                    "multiline": True,
                    "default": "{}"
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)
    FUNCTION = "run_command_with_json"
    CATEGORY = "Custom/Utility"

    @classmethod
    def IS_CHANGED(cls, executable, json_input, seed):
        # Create a hash of inputs to detect changes
        import hashlib
        hash_input = f"{executable}_{json_input}_{seed}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def run_command_with_json(self, executable, json_input, seed):
        # Validate JSON input
        try:
            # Try to parse the JSON to validate it
            json.loads(json_input)
        except json.JSONDecodeError as e:
            return (f"[ERROR] Invalid JSON input: {e}",)

        # Build command list with --json-str argument
        cmd = [
            executable,
            "--json-str",
            json_input,
        ]

        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        except subprocess.CalledProcessError as e:
            result = f"[ERROR] Code {e.returncode}:\n{e.output}"
        except FileNotFoundError:
            result = f"[ERROR] Executable not found: {executable}"
        except Exception as e:
            result = f"[ERROR] {type(e).__name__}: {e}"

        return (result,)


# Registro do node no ComfyUI
NODE_CLASS_MAPPINGS = {
    "CommandExecNode": CommandExecNode,
    "CommandExecJsonNode": CommandExecJsonNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CommandExecNode": "Terminal",
    "CommandExecJsonNode": "Terminal JSON"
}
