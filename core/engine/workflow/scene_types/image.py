"""Image scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle
import workflow.scene_types.image_with_caption as image_with_caption
async def create_image_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    # Reuse the caption scene implementation; callers can provide either image_path or image_prompt.
    scene['text'] = '&nbsp;'
    return await image_with_caption.create_image_with_caption_scene(scene, style)
