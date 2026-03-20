"""Top-level package for comfyui_gfpgan."""

# Patch for newer torchvision versions that removed functional_tensor module.
# basicsr.data.degradations imports rgb_to_grayscale from the old location.
import sys
import types
try:
    import torchvision.transforms.functional_tensor  # noqa: F401
except ModuleNotFoundError:
    from torchvision.transforms.functional import rgb_to_grayscale
    _mod = types.ModuleType("torchvision.transforms.functional_tensor")
    _mod.rgb_to_grayscale = rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = _mod

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    
]

__author__ = """Luca"""
__email__ = "luca@upsampler.com"
__version__ = "0.0.1"

from .src.comfyui_gfpgan.nodes import NODE_CLASS_MAPPINGS
from .src.comfyui_gfpgan.nodes import NODE_DISPLAY_NAME_MAPPINGS


