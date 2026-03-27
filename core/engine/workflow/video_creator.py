import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Literal, Annotated
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from pathlib import Path
import shutil
# Import Pydantic BaseModel for structured responses
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import TypedDict
from langgraph.managed.is_last_step import RemainingSteps
from json_repair import repair_json
import subprocess
import uuid

from image_service import generate_image_from_prompt
from .llm_adapter import WorkflowLLMAdapter

# Import VideoStyle from separate module to avoid circular imports
from .VideoStyle import VideoStyle
from .scene_types.shared import get_or_create_voice_audio
from .scene_types.shared import copy_file_to_path, get_media_duration, resolve_project_file_path

# Import scene type modules
from .scene_types import (
    create_text_only_scene,
    create_bullet_list_scene,
    create_image_scene,
    create_image_with_caption_scene,
    create_icon_grid_scene,
    create_mermaid_diagram_scene,
    create_code_snippet_scene,
    create_table_scene,
    create_split_screen_scene,
    create_quiz_scene,
    create_definition_scene,
    create_text_animation_scene,
    create_narration_only_scene,
    create_host_speech_clip_scene,
    create_video_clip_scene,
)

from logger import log, error


class SceneType(Enum):
    TEXT_ONLY = "text_only"
    BULLET_LIST = "bullet_list"
    IMAGE = "image"
    IMAGE_WITH_CAPTION = "image_with_caption"
    ICON_GRID = "icon_grid"
    MERMAID_DIAGRAM = "mermaid_diagram"
    CODE_SNIPPET = "code_snippet"
    TABLE = "table"
    SPLIT_SCREEN = "split_screen"
    QUIZ = "quiz"
    DEFINITION_SCENE = "definition"
    TEXT_ANIMATION_SCENE = "text_animation"
    NARRATION_ONLY = "narration_only"
    HOST_SPEECH_CLIP = "host_speech_clip"
    VIDEO_CLIP = "video_clip"


@dataclass
class VideoSpec:
    requirement: str
    duration: int  # Duration in seconds
    resolution: str  # e.g., "1920x1080", "1280x720"
    title: str
    description: str
    core_message: str
    scope_notes: str
    other_requirements: str
    target_audience: str
    learning_objectives: List[str]
    is_dialog: bool


@dataclass
class Scene:
    scene_id: str
    data: Dict[str, Any]  # Contains all scene-specific data including scene_type
    video_file_path: Optional[str] = None  # Path to generated scene video


class VideoSpecification(BaseModel):
    title: str
    description: str
    target_audience: str
    learning_objectives: List[str]
    total_duration: int
    resolution: str


class ScenePlan(BaseModel):
    scenes: List[Dict[str, Any]]
    total_estimated_duration: int


class State(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: RemainingSteps
    thread_id: str

    # Input parameters
    requirement: str
    target_duration: int
    resolution: str
    output_path: str

    # Workflow state
    video_spec: Optional[VideoSpec]
    video_style: Optional[VideoStyle]  # Shared style configuration for all scenes
    scene_plan: Optional[List[Scene]]
    scene_videos: List[str]  # List of generated scene video file paths
    final_video_path: Optional[str]
    run_output_dir: Optional[str]

    # Processing state
    current_scene_index: int
    total_scenes: int


class VideoCreatorWorkflow:
    """LangGraph workflow for creating educational videos"""

    IMAGE_SCENE_TYPES = {
        SceneType.IMAGE.value,
        SceneType.IMAGE_WITH_CAPTION.value,
    }

    HOST_IMAGE_SCENE_TYPES = {
        SceneType.HOST_SPEECH_CLIP.value,
    }

    def __init__(self):
        self.max_retries = 3
        self.recursion_limit = 50

        # Initialize LLM
        self.llm = self._init_llm()
        self.plan_llm = self._init_plan_llm()

        # Build workflow graph
        self.graph = self._build_graph()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        await self.close()
        return False

    async def close(self):
        """Cleanup resources before shutdown"""
        try:
            # Close LLM clients if they expose an async HTTP client
            llm_client = getattr(self.llm, 'async_client', None)
            if llm_client and hasattr(llm_client, 'aclose'):
                await llm_client.aclose()
                self.llm = None

            plan_client = getattr(self.plan_llm, 'async_client', None)
            if plan_client and hasattr(plan_client, 'aclose'):
                await plan_client.aclose()
                self.plan_llm = None
        except Exception as err:
            log(f"Error during cleanup: {err}")
    
    def _init_llm(self):
        """Initialize the LLM model based on environment configuration"""
        return WorkflowLLMAdapter()
    
    def _init_plan_llm(self):
        """Initialize the LLM model based on environment configuration"""
        return WorkflowLLMAdapter()
    
    def _build_graph(self) -> StateGraph:
        """Build the workflow graph with nodes and edges"""
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("design_video_spec", self.design_video_spec_node)
        workflow.add_node("initialize_style", self.initialize_style_node)
        workflow.add_node("plan_scenes", self.plan_scenes_node)
        workflow.add_node("create_scene", self.create_scene_node)
        workflow.add_node("merge_scenes", self.merge_scenes_node)
        
        # Add edges
        workflow.add_edge(START, "design_video_spec")
        workflow.add_edge("design_video_spec", "initialize_style")
        workflow.add_edge("initialize_style", "plan_scenes")
        workflow.add_edge("plan_scenes", "create_scene")
        
        # create_scene will use Command to decide next step (either loop back to create_scene or go to merge_scenes)
        workflow.add_edge("merge_scenes", END)
        
        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    async def design_video_spec_node(self, state: State) -> Dict[str, Any]:
        """Design video specification by refining input with LLM"""
        log("Designing video specification...")
        
        requirement = state.get("requirement", "")
        target_duration = state.get("target_duration", 60)  # Default 1-minute
        resolution = state.get("resolution", "1080x1920")

        if not requirement:
            raise ValueError("Requirement must be provided to design video specification")
        
        system_prompt = f"""\
You are an expert educational designer, and your task is to act as the first step in a two-part video creation workflow. Your goal is to take a user's raw educational request and transform it into a foundational blueprint for an educational video. This blueprint will be passed to another AI responsible for creating the detailed, scene-by-scene video plan.

## Educational Philosophy
In the age of AI, students need broad foundational understanding rather than deep technical expertise. Focus on creating "professional common sense" - knowledge that helps students guide AI tools effectively and apply concepts in practice.

## Your Task
Analyze the user's request and create a specification for a {target_duration}-second educational video:

1. If the request is vague or broad, narrow it to a specific, teachable concept
2. Focus on memorable, practical knowledge (breadth over depth)  
3. Ensure the content prepares students to work with AI tools
4. Consider what can realistically be taught in {target_duration} seconds
5. Extract and use all context information provided in the requirement to tailor the content appropriately

Return your response in JSON format:
{{
    "title": "string - Concise, engaging title (max 60 characters)",
    "description": "string - What the video teaches and why it matters (2-3 sentences)",
    "target_audience": "string - Specific grade level, age range, or expertise level",
    "learning_objectives": [
        "Students will understand...",
        "Students will be able to...",
        "Students will recognize..."
    ],
    "core_message": "string - The ONE key takeaway students should remember",
    "scope_notes": "string - Brief guidance on what to focus on given the {target_duration}-second constraint",
    "other_requirements": "string - Any additional requirements or constraints (e.g., specific style, tone, format, output language, or voice-over language, etc.)",
    "is_dialog": "boolean - True if the requirement indicates a dialog/podcast/conversation style video, False for regular educational video format. Look for keywords like 'dialog', 'conversation', 'podcast', 'interview', 'discussion', 'Q&A', or similar conversational formats in the requirement."
}}

The title and description will be used in the video metadata for students and audiences, so make them clear and engaging. The learning objectives should be specific and measurable.
Do not include any video duration requirements or other constraints in the description or learning objectives.
"""

        human_prompt = f"""Please create a video specification for the following requirement:

Requirement: {requirement}
Target Duration: {target_duration} seconds

Please analyze the requirement and extract all contextual information to create a personalized and effective educational video."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages, config={
                "configurable": {
                    "model_kwargs": {"response_format": {"type": "json_object"}}
                }
            })

            # Parse JSON response
            content = response.content.strip()
            log(f"design_video_spec_node LLM response content: {content}")
            content = repair_json(content)
            spec_data = json.loads(content)

            video_spec = VideoSpec(
                requirement=requirement,
                duration=target_duration,
                resolution=resolution,
                title=spec_data.get("title", f"{requirement}"),
                description=spec_data.get("description", ""),
                core_message=spec_data.get("core_message", ""),
                scope_notes=spec_data.get("scope_notes", ""),
                other_requirements=spec_data.get("other_requirements", ""),
                target_audience=spec_data.get("target_audience", "General learners"),
                learning_objectives=spec_data.get("learning_objectives", []),
                is_dialog=spec_data.get("is_dialog", False)
            )
            
            log(f"Video specification created: {video_spec.title}")
            
            return {
                "video_spec": video_spec,
                "messages": state.get('messages', []) + [response]
            }
            
        except Exception as e:
            log(f"Error in design_video_spec_node: {e}")
            return {
                "messages": [AIMessage(content=f"Error creating video specification: {str(e)}")]
            }
    
    async def initialize_style_node(self, state: State) -> Dict[str, Any]:
        """Initialize video style configuration based on video spec"""
        log("Initializing video style configuration...")
        
        video_spec = state.get("video_spec")
        
        if not video_spec:
            return {"messages": [AIMessage(content="Error: No video specification found")]}
        
        # Parse resolution from video spec
        resolution_parts = video_spec.resolution.lower().split('x')
        width = int(resolution_parts[0]) if len(resolution_parts) >= 2 else 1920
        height = int(resolution_parts[1]) if len(resolution_parts) >= 2 else 1080
        
        # Create default style configuration with voice name
        video_style = VideoStyle(
            width=width,
            height=height
        )
        
        log(f"Video style initialized: {width}x{height}")
        
        return {
            "video_style": video_style,
            "messages": [AIMessage(content=f"Video style configured for {width}x{height} resolution")]
        }
    
    async def plan_scenes_node(self, state: State) -> Dict[str, Any]:
        """Plan scenes for the video using LLM"""
        log("Planning video scenes...")
        
        video_spec = state.get("video_spec")
        video_style = state.get("video_style")
        
        if not video_spec:
            return {"messages": [AIMessage(content="Error: No video specification found")]}
        
        # Dialog-specific voice-over guidelines
        dialog_guidelines = ""
        if video_spec.is_dialog:
            dialog_guidelines = """
## Dialog Video Guidelines

Since this is a dialog/podcast-style video, format ALL voice-over text as a conversation between a Host and Guest:

* **Always use the format**: `Host: [text]` and `Guest: [text]`
* **Make it natural**: Write as if two people are having a genuine conversation about the topic
* **Use neutral names**: Refer to "Host" and "Guest" rather than specific gender-based names
* **Keep it engaging**: Make the dialog feel like a natural podcast conversation
* **Balance participation**: Both Host and Guest should contribute meaningfully to the explanation
* **Transitions**: Use natural conversation transitions like "That's interesting, Guest..." or "Exactly, Host..."

Example format:
```
Host: Welcome everyone! Today we're exploring machine learning basics. What would you say is the most important thing beginners should know?
Guest: Great question! I'd say understanding the difference between supervised and unsupervised learning is crucial. Host, how would you explain supervised learning?
Host: Perfect! Supervised learning is like having a teacher guide you with examples...
```

**Important**: Every voice-over field must be formatted as dialog.
"""
        
        system_prompt = f"""\
## Your Role

You are an expert educational video producer specializing in AI-era learning. Your mission is to create concise, memorable educational content that prepares students to effectively collaborate with AI tools.

## Educational Philosophy

In the age of AI, students need broad foundational understanding rather than deep technical expertise. Your videos should teach concepts that become "professional common sense" - knowledge students can:

* Use to guide AI tools effectively
* Apply in research and problem-solving
* Recall quickly when needed in practice

## Your Mission

Design a {video_spec.duration}-second educational video, using multiple scenes. Your primary objectives:

* Structure the scenes in a logical, smooth progression that effectively teaches the concept.
* Use a professional and clear educational tone.
* Make the content engaging, concise, and easy to recall for long-term retention.

{dialog_guidelines}

## Voice-Over Text Guidelines

When writing voice-over scripts for each scene:

* Write in a **clear, natural, and professional tone**, like a teacher guiding students.
* Keep sentences **concise and easy to follow**, especially for younger or non-native English learners.
* Use **everyday language** where possible to ensure accessibility.
* Break long explanations into **multiple sentences**, using punctuation like `?`, `!`, `;`, or `.` to indicate pauses or sentence ends.
* Emphasize key points **at the start or end** of sentences for better retention.
* Make sure the **voice-over aligns with the visual element** — describe or reinforce what is shown on screen.

The total duration of all voice-overs combined should match the target video duration of **{video_spec.duration} seconds** when read at a natural pace (~130-150 words per minute).

## Image Generation Prompt Guidelines
Write prompts that are **precise, structured, and layout-aware** so images slot cleanly into video edits.

**1) Purpose & audience (1 line)**
- State lesson goal + learner level/age to set tone.

**2) Composition & layers**
- Specify **foreground / midground / background** elements and their relationships.
- Reserve **safe areas** for UI: e.g., “leave 96 px top margin for title; 180 px bottom margin for subtitles.”

**3) Visual language**
- Style (e.g., clean flat infographic / chalkboard sketch / isometric / Pixar-like 3D / watercolor).
- Color palette: list 3–5 colors + **contrast intent** (e.g., “high contrast labels”).
- Lighting & mood (bright classroom / neutral studio / soft ambient).
- POV/composition (eye-level, rule-of-thirds, centered subject, top-down, isometric).

**4) Concept transitions / blends**
- If combining ideas, describe the **bridge** (e.g., “left: solid → middle: liquid → right: gas; gradient blend with arrows”).

**5) Materials & textures (when relevant)**
- Call out **see-through materials** (glass, water, plastic) and surface qualities (matte, glossy, roughness, refraction).

**6) On-image text (use only when necessary)**
- Provide **exact wording**, font family (with generic fallback), weight/size, color, alignment, placement grid, effects (outline/shadow/glow).
- Prefer **text-only scenes** for dense text to avoid rendering artifacts.

**7) Technical constraints (explicit)**
- Negative list: `no watermarks, no extra text, no brand logos`.

### Reusable mini-template for image prompts
- Purpose/Audience: [one line]
- Style & Look: [style], [palette], [lighting/mood], [POV/composition]
- Scene Layers:
  - Foreground: [...]
  - Midground: [...]
  - Background: [...]
- Transition/Blend: [if applicable]
- Materials/Textures: [if applicable]
- Text on Image: [exact text + font/size/color/placement/effects] or “none”
- Technical: safe areas=[top/bottom px], negative=[...]

**Avoid using images to display text only content unless absolutely necessary.**
**Avoid using images to display coding text even with a window or terminal frame, using code snippet scenes instead.**
**For any scene or icon that supports `image_prompt` and `image_path`, provide exactly one of them, never both.**
**Only set `image_path` when a source image file is specified in the video design requirements.**
**If the user provided a local image file with a description, prefer `image_path` and use the description only to decide scene structure/caption/voice-over.**
**Only use `image_prompt` when an image must be generated by AI.**
**For any scene with `voice_over`, `voice_over` is still required even if `voice_path` is provided.**
**Only set `voice_path` when a source voice file is specified in the video design requirements; otherwise generate audio from `voice_over`.**

## Supported Scene Types

Below are the available scene types you can use. Each scene type must follow the structure exactly as shown. Use them strategically to explain the knowledge point.

* Text Only – Single line of highlighted text, ideal for emphasising a key term or concept. It will be put in the middle of the screen, for long text, it should be auto wrap and left align
```json
{{
  "scene_type": "text_only",
  "text": "string - shown in the screen",
  "voice_over": "string",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Bullet List – Multiple bullet points, for listing definitions, steps, or features. The list should be in the middle of the screen, and the string list items are left align and auto wrap for long item.
```json
{{
  "scene_type": "bullet_list",
  "items": ["string - item text shown in the screen"],
  "voice_over": "string",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Image – Full-screen static image or illustration without overlaid text.
```json
{{
  "scene_type": "image",
  "image_path": "string - set only if an image file is specified in the video design requirements, OR omit this and use image_prompt",
  "image_prompt": "string - AI prompt which will be used to create the image, OR omit this and use image_path",
  "voice_over": "string",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Image With Caption – Static image with a short descriptive caption. The caption is in the bottom of the image with a line height margin on the top.
```json
{{
  "scene_type": "image_with_caption",
  "image_path": "string - set only if an image file is specified in the video design requirements, OR omit this and use image_prompt",
  "image_prompt": "string - AI prompt which will be used to create the image, OR omit this and use image_path",
  "text": "string - caption of the image",
  "voice_over": "string",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Icon Grid – Multiple small icons or illustrations arranged in a grid, each representing an idea, max 4 icons per scene. For each icon, the text will be under the icon.
```json
{{
  "scene_type": "icon_grid",
  "icons": [
    {{
      "image_path": "string - set only if an image file is specified in the video design requirements, OR omit this and use image_prompt",
      "image_prompt": "string - use to create the icon image with AI, OR omit this and use image_path",
      "text": "string - the caption of the image"
    }}
  ],
  "voice_over": "string",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Mermaid Diagram – Use Mermaid syntax to render flowcharts, sequence diagrams, etc. We do only support type: `flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`,`erDiagram`, `pie`, `mindmap` and `timeline`
```json
{{
  "scene_type": "mermaid_diagram",
  "diagram_type": "flowchart, sequenceDiagram, classDiagram, stateDiagram-v2, erDiagram, pie, mindmap or timeline",
  "description": "string - the detail of the diagram, which we will use AI to create the mermaid diagram code",
  "text": "string - caption of the diagram",
  "voice_over": "string",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Code Snippet – A formatted code block with syntax highlighting for a specific programming language.
```json
{{
  "scene_type": "code_snippet",
  "language": "string - programming language for syntax highlighting, e.g., 'python', 'javascript'",
  "code": "Markdown code block — enclosed by three backticks, ideally no more than 7 lines",
  "voice_over": "The text for voice-over to explain the code snippet for the knowledge point.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Table – Tabular data presentation, useful for comparisons or numeric data. We will use the table content by a html table, Including the rows or cols caption in the rows array if applicable
```json
{{
  "scene_type": "table",
  "rows": [
    ["string"]
  ],
  "text": "string - caption of the table",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Split-Screen – Two short string items shown side-by-side for direct comparison.
```json
{{
  "scene_type": "split_screen",
  "text1": "string",
  "text2": "string",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Quiz – Multiple-choice questions, 4 options and only one is correct.
```json
{{
  "scene_type": "quiz",
  "question": "string",
  "options": ["string"],
  "answer": "number - the correct index of the options, start from 0",
  "question_voice_over": "use to explain the question for student to answer",
  "answer_voice_over": "use to explain which option is correct"
}}
```

* Definition – Term and its definition in markdown style.
```json
{{
  "scene_type": "definition",
  "term": "string",
  "definition": "Definition in markdown style. It can be a code block for code statements, LaTeX for math or physics equations, or rich markdown text to explain the concept.",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Text Animation – Pure text animated for a short text with html5/css, we will only support type: 'fade-in', 'slide-in' ,'typewriter', 'blink' or 'scale-up'
This scene type is ideal for emphasizing titles, key points, or important concepts. Ensure the voice-over duration matches or slightly exceeds the animation duration for a smooth and synchronized experience.
```json
{{
  "scene_type": "text_animation",
  "animation_type": "string: 'fade-in', 'slide-in' ,'typewriter', 'blink' or 'scale-up'",
  "text": "string - the text for animation",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements; supports absolute path or project-root-relative path"
}}
```

* Narration Only –  Audio narration with a static background (no visuals or text).
```json
{{
  "scene_type": "narration_only",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Host Speech Clip – Talking head or lipsynced host scene driven by a host image or source video.
```json
{{
  "scene_type": "host_speech_clip",
  "video_type": "string: 'talk_video' or 'lipsync', default 'talk_video'",
  "host_image_path": "string - set only if a source host image file is specified; if present, ignore host_image_prompt",
  "host_image_prompt": "string - use only when host_image_path is not provided",
  "talking_video_prompt": "string - guidance for the host talking animation style",
  "video_path": "string - optional existing source video; if it already has audio, it is treated as the final scene video",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

* Video Clip – Existing video clip combined with scene narration.
```json
{{
  "scene_type": "video_clip",
  "video_path": "string - required source video file path",
  "voice_over": "The text for voice-over.",
  "voice_path": "string - set only if a voice file is specified in the video design requirements"
}}
```

Return your full video plan as a JSON object:

{{
    "scenes": [
        {{
            "scene_type": "text_only",
            "text": "string - shown in the screen",
            "voice_over": "string",
            "voice_path": "string - set only if a voice file is specified in the video design requirements"
        }},
        {{
            "scene_type": "bullet_list",
            "items": ["string - item text"],
            "voice_over": "string",
            "voice_path": "string - set only if a voice file is specified in the video design requirements"
        }}
    ]
}}

This is just a sample structure. Your actual video plan must:
- Select scene types that best match each concept (visual for processes, text for definitions, etc.)
- Flow logically from introduction → explanation → conclusion/application
- Prioritize clarity and retention over trying to cover too much
- Match the specified total length of {{video_spec.duration}} seconds

Remember: 
- Each scene should serve a clear pedagogical purpose. Choose scenes that make abstract concepts concrete and help students build mental models they can use when working with AI tools.
- Avoid mentioning AI or its assistance in the video unless it is specifically required in the video plan. Focus solely on teaching the core knowledge point to ensure clarity and educational value.
— Please think step-by-step to ensure selecting the best scene types and structuring them effectively for maximum impact for student learning.
"""

        human_prompt = f"""Please create a detailed scene plan for this video:

Title: {video_spec.title}
Description: {video_spec.description}
Target Duration: {video_spec.duration} seconds
Learning Objectives: {', '.join(video_spec.learning_objectives)}
Target Audience: {video_spec.target_audience}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            response = await self.plan_llm.ainvoke(messages, config={
                "configurable": {
                    "model_kwargs": {"response_format": {"type": "json_object"}}
                }
            })

            content = response.content.strip()
            log(f"plan_scenes_node LLM response content: {content}")
            content = repair_json(content)
            plan_data = json.loads(content)
            
            # Convert response to Scene objects using new structure
            scenes = []
            for i, scene_data in enumerate(plan_data.get("scenes", [])):
                scene = Scene(
                    scene_id=f"scene_{i+1}",
                    data=scene_data  # Store all scene data in the data field
                )
                scenes.append(scene)
            
            log(f"Created scene plan with {len(scenes)} scenes")
            
            return {
                "scene_plan": scenes,
                "total_scenes": len(scenes),
                "current_scene_index": 0,
                "messages": state.get('messages', []) + [response]
            }
            
        except Exception as e:
            log(f"Error in plan_scenes_node: {e}")
            return {
                "messages": [AIMessage(content=f"Error creating scene plan: {str(e)}")]
            }
        
    async def create_scene_video_by_type(
        self,
        scene: Dict[str, Any],
        style: VideoStyle,
    ) -> str:
        """
        Create a scene video based on the scene type.
        This function calls the appropriate scene type module to generate the video.

        Args:
            scene: Scene data dictionary containing scene_type and all scene-specific data
            style: Video style configuration for consistent styling
        Returns:
            Local file path to the generated scene video
        """
        
        # Extract scene type from scene data
        scene_type_str = scene.get("scene_type")
        if not scene_type_str:
            raise ValueError("Scene data must contain 'scene_type' field")
        
        try:
            scene_type = SceneType(scene_type_str)
        except ValueError:
            raise ValueError(f"Unsupported scene type: {scene_type_str}")
        
        # Map scene types to their corresponding functions
        scene_creators = {
            SceneType.TEXT_ONLY: create_text_only_scene,
            SceneType.BULLET_LIST: create_bullet_list_scene,
            SceneType.IMAGE: create_image_scene,
            SceneType.IMAGE_WITH_CAPTION: create_image_with_caption_scene,
            SceneType.ICON_GRID: create_icon_grid_scene,
            SceneType.MERMAID_DIAGRAM: create_mermaid_diagram_scene,
            SceneType.CODE_SNIPPET: create_code_snippet_scene,
            SceneType.TABLE: create_table_scene,
            SceneType.SPLIT_SCREEN: create_split_screen_scene,
            SceneType.QUIZ: create_quiz_scene,
            SceneType.DEFINITION_SCENE: create_definition_scene,
            SceneType.TEXT_ANIMATION_SCENE: create_text_animation_scene,
            SceneType.NARRATION_ONLY: create_narration_only_scene,
            SceneType.HOST_SPEECH_CLIP: create_host_speech_clip_scene,
            SceneType.VIDEO_CLIP: create_video_clip_scene,
        }
        
        # Get the appropriate scene creator function
        creator_func = scene_creators.get(scene_type)
        if not creator_func:
            raise ValueError(f"Unsupported scene type: {scene_type}")
        
        try:
            return await creator_func(scene, style)
        except Exception as e:
            error(f"Error creating {scene_type.value} scene: {e}")
            raise Exception(f"Failed to create scene of type {scene_type.value}: {str(e)}")

    def _create_run_output_dir(self, output_path: str, thread_id: str) -> str:
        base_dir = Path(output_path or "/tmp").expanduser().resolve()
        run_id = f"video_run_{thread_id.replace('/', '_')}"
        run_dir = base_dir / run_id
        (run_dir / "scenes").mkdir(parents=True, exist_ok=True)
        return str(run_dir)

    def _ensure_scene_dir(self, run_output_dir: str, scene_id: str) -> Path:
        scene_dir = Path(run_output_dir) / "scenes" / scene_id
        scene_dir.mkdir(parents=True, exist_ok=True)
        return scene_dir

    def _stage_scene_file(
        self,
        source_path: str,
        destination_path: Path,
        cleanup_source: bool = False,
    ) -> str:
        staged_path = copy_file_to_path(source_path, str(destination_path))
        if cleanup_source:
            try:
                resolved_source = Path(source_path).expanduser().resolve()
                if resolved_source != Path(staged_path).resolve() and resolved_source.exists():
                    resolved_source.unlink()
            except OSError:
                pass
        return staged_path

    def _extract_extension(self, file_path: str, default: str) -> str:
        suffix = Path(file_path).suffix.lower()
        return suffix if suffix else default

    def _normalize_scene_video(self, input_path: str, output_path: str, style: VideoStyle) -> str:
        video_filter = (
            f"scale={style.width}:{style.height}:force_original_aspect_ratio=increase,"
            f"crop={style.width}:{style.height},fps=30"
        )
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            output_path,
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to normalize scene video: {result.stderr}")
        return output_path

    def _ensure_scene_preview_image(self, scene_data: Dict[str, Any], scene_video_path: str, scene_dir: Path) -> None:
        if scene_data.get("audit_image_path") and Path(str(scene_data["audit_image_path"])).is_file():
            return

        preview_path = scene_dir / "image.png"
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            scene_video_path,
            "-frames:v",
            "1",
            str(preview_path),
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and preview_path.exists():
            scene_data["audit_image_path"] = str(preview_path)

    def _write_audit_readme(self, run_output_dir: str, state_values: Dict[str, Any]) -> None:
        output_dir = Path(run_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Video Audit",
            "",
            f"- Requirement: {state_values.get('requirement', '')}",
        ]

        video_spec = state_values.get("video_spec")
        if video_spec:
            lines.append(f"- Resolution: {getattr(video_spec, 'resolution', '')}")
            lines.append(f"- Target duration: {getattr(video_spec, 'duration', '')}")

        final_video_path = state_values.get("final_video_path") or ""
        if final_video_path:
            lines.append(f"- Final video: `{final_video_path}`")

        scene_plan = state_values.get("scene_plan") or []
        lines.extend(["", "## Scenes", ""])
        for index, scene in enumerate(scene_plan, start=1):
            scene_data = scene.data if isinstance(scene, Scene) else getattr(scene, "data", {}) or {}
            scene_id = scene.scene_id if isinstance(scene, Scene) else f"scene_{index:03d}"
            lines.append(f"### {scene_id}")
            lines.append(f"- Scene type: {scene_data.get('scene_type', '')}")
            if scene_data.get("audit_image_path"):
                lines.append(f"- Image: `{scene_data['audit_image_path']}`")
            if scene_data.get("voice_path"):
                lines.append(f"- Audio: `{scene_data['voice_path']}`")
            if scene_data.get("question_voice_path"):
                lines.append(f"- Question audio: `{scene_data['question_voice_path']}`")
            if scene_data.get("answer_voice_path"):
                lines.append(f"- Answer audio: `{scene_data['answer_voice_path']}`")
            if getattr(scene, "video_file_path", None):
                lines.append(f"- Scene video: `{scene.video_file_path}`")
            lines.append("")

        (output_dir / "README.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    async def _prepare_scene_images(self, scene_plan: List[Scene]) -> None:
        """Pre-generate all AI images before scene video rendering."""
        for scene in scene_plan:
            scene_data = scene.data
            scene_type = scene_data.get("scene_type")
            scene_dir = Path(scene_data.get("_scene_dir") or "")
            if not scene_dir:
                raise ValueError(f"Missing scene directory for {scene.scene_id}")

            if scene_type in self.IMAGE_SCENE_TYPES:
                image_prompt = scene_data.get("image_prompt", "")
                image_path = scene_data.get("image_path", "")

                if image_prompt and image_path:
                    raise ValueError(
                        f"Scene {scene.scene_id} requires exactly one of 'image_prompt' or 'image_path'"
                    )

                if image_prompt:
                    log(f"Generating image for {scene.scene_id}")
                    generated_image_path = await generate_image_from_prompt(
                        image_prompt,
                        style="icon",
                    )
                    if not generated_image_path:
                        raise Exception(f"Failed to generate image for {scene.scene_id}")

                    staged_image_path = self._stage_scene_file(
                        generated_image_path,
                        scene_dir / "image.png",
                        cleanup_source=True,
                    )
                    scene_data["image_path"] = staged_image_path
                    scene_data["image_url"] = staged_image_path
                    scene_data["audit_image_path"] = staged_image_path
                    scene_data.pop("image_prompt", None)
                elif image_path:
                    resolved_image_path = resolve_project_file_path(image_path, "image_path")
                    staged_image_path = self._stage_scene_file(
                        resolved_image_path,
                        scene_dir / f"image{self._extract_extension(resolved_image_path, '.png')}",
                    )
                    scene_data["image_path"] = staged_image_path
                    scene_data["image_url"] = staged_image_path
                    scene_data["audit_image_path"] = staged_image_path
                continue

            if scene_type != SceneType.ICON_GRID.value:
                if scene_type not in self.HOST_IMAGE_SCENE_TYPES:
                    continue
                host_image_path = scene_data.get("host_image_path", "")
                host_image_prompt = scene_data.get("host_image_prompt", "")
                if host_image_path:
                    resolved_host_image_path = resolve_project_file_path(host_image_path, "host_image_path")
                    staged_host_image_path = self._stage_scene_file(
                        resolved_host_image_path,
                        scene_dir / f"host_image{self._extract_extension(resolved_host_image_path, '.png')}",
                    )
                    scene_data["host_image_path"] = staged_host_image_path
                    scene_data["audit_image_path"] = staged_host_image_path
                    scene_data.pop("host_image_prompt", None)
                    continue
                if host_image_prompt:
                    generated_host_image_path = await generate_image_from_prompt(
                        host_image_prompt,
                        style="icon",
                    )
                    if not generated_host_image_path:
                        raise Exception(f"Failed to generate host image for {scene.scene_id}")
                    staged_host_image_path = self._stage_scene_file(
                        generated_host_image_path,
                        scene_dir / "host_image.png",
                        cleanup_source=True,
                    )
                    scene_data["host_image_path"] = staged_host_image_path
                    scene_data["audit_image_path"] = staged_host_image_path
                    scene_data.pop("host_image_prompt", None)
                continue

            icons = scene_data.get("icons", [])
            for index, icon in enumerate(icons):
                image_prompt = icon.get("image_prompt", "")
                image_path = icon.get("image_path", "")

                if image_prompt and image_path:
                    raise ValueError(
                        f"Scene {scene.scene_id} icon {index + 1} requires exactly one of 'image_prompt' or 'image_path'"
                    )

                if not image_prompt:
                    if image_path:
                        resolved_icon_path = resolve_project_file_path(image_path, f"icons[{index}].image_path")
                        staged_icon_path = self._stage_scene_file(
                            resolved_icon_path,
                            scene_dir / f"icon_{index + 1:02d}{self._extract_extension(resolved_icon_path, '.png')}",
                        )
                        icon["image_path"] = staged_icon_path
                        icon["image_url"] = staged_icon_path
                        if index == 0:
                            scene_data["audit_image_path"] = staged_icon_path
                    continue

                log(f"Generating icon {index + 1} for {scene.scene_id}")
                generated_image_path = await generate_image_from_prompt(
                    image_prompt,
                    style="icon",
                )
                if not generated_image_path:
                    raise Exception(
                        f"Failed to generate icon {index + 1} for {scene.scene_id}"
                    )

                staged_icon_path = self._stage_scene_file(
                    generated_image_path,
                    scene_dir / f"icon_{index + 1:02d}.png",
                    cleanup_source=True,
                )
                icon["image_path"] = staged_icon_path
                icon["image_url"] = staged_icon_path
                if index == 0:
                    scene_data["audit_image_path"] = staged_icon_path
                icon.pop("image_prompt", None)

    async def _prepare_scene_audio(
        self,
        scene_plan: List[Scene],
        video_style: VideoStyle,
    ) -> None:
        """Pre-generate all scene narration audio before scene video rendering."""
        for scene in scene_plan:
            scene_data = scene.data
            scene_type = scene_data.get("scene_type")
            scene_dir = Path(scene_data.get("_scene_dir") or "")
            if not scene_dir:
                raise ValueError(f"Missing scene directory for {scene.scene_id}")

            if scene_type == SceneType.QUIZ.value:
                for voice_key, path_key, meta_key, url_key in (
                    ("question_voice_over", "question_voice_path", "_generated_question_voice_path", "question_voice_url"),
                    ("answer_voice_over", "answer_voice_path", "_generated_answer_voice_path", "answer_voice_url"),
                ):
                    voice_over = scene_data.get(voice_key, "")
                    voice_path = scene_data.get(path_key, "")
                    audio_path, should_cleanup_audio = await get_or_create_voice_audio(
                        voice_over,
                        voice_path,
                        video_style.voice_name,
                    )

                    if not audio_path:
                        raise Exception(f"Failed to generate audio for {scene.scene_id}:{voice_key}")

                    destination_name = "question_audio.wav" if "question" in path_key else "answer_audio.wav"
                    staged_audio_path = self._stage_scene_file(
                        audio_path,
                        scene_dir / destination_name,
                        cleanup_source=should_cleanup_audio,
                    )
                    scene_data[path_key] = staged_audio_path
                    scene_data[url_key] = staged_audio_path
                continue

            voice_over = scene_data.get("voice_over", "")
            voice_path = scene_data.get("voice_path", "")

            if not voice_over and not voice_path:
                continue

            log(f"Generating audio for {scene.scene_id}")
            audio_path, should_cleanup_audio = await get_or_create_voice_audio(
                voice_over,
                voice_path,
                video_style.voice_name,
            )

            if not audio_path:
                raise Exception(f"Failed to generate audio for {scene.scene_id}")

            destination_name = f"audio{self._extract_extension(audio_path, '.wav')}"
            staged_audio_path = self._stage_scene_file(
                audio_path,
                scene_dir / destination_name,
                cleanup_source=should_cleanup_audio,
            )
            scene_data["voice_path"] = staged_audio_path
            scene_data["voice_url"] = staged_audio_path

    async def _prepare_scene_assets(
        self,
        scene_plan: List[Scene],
        video_style: VideoStyle,
    ) -> None:
        """Generate reusable media assets in batches before scene rendering."""
        try:
            log("Preparing scene images...")
            await self._prepare_scene_images(scene_plan)
            log("Preparing scene audio...")
            await self._prepare_scene_audio(scene_plan, video_style)
        except Exception:
            raise
    
    async def create_scene_node(self, state: State) -> Command[Literal["create_scene", "merge_scenes"]]:
        """Create a scene with video URL and decide next step"""
        scene_plan = state.get("scene_plan", [])
        current_scene_index = state.get("current_scene_index", 0)
        scene_videos = state.get("scene_videos", [])
        video_style = state.get("video_style")
        run_output_dir = state.get("run_output_dir")

        if not scene_plan:
            raise ValueError("No scene plan found in state")

        if not video_style:
            raise ValueError("No video style configuration found in state")
        if not run_output_dir:
            raise ValueError("No output directory found in state")

        if current_scene_index >= len(scene_plan):
            raise ValueError("Scene index out of range")

        for scene in scene_plan:
            if not scene.data.get("_scene_dir"):
                scene.data["_scene_dir"] = str(self._ensure_scene_dir(run_output_dir, scene.scene_id))

        current_scene = scene_plan[current_scene_index]
        current_scene_dir = Path(current_scene.data["_scene_dir"])

        log(f"Creating scene {current_scene_index + 1}/{len(scene_plan)}: {current_scene.scene_id}")

        if current_scene_index == 0 and not scene_videos:
            await self._prepare_scene_assets(scene_plan, video_style)

        video_path = await self.create_scene_video_by_type(current_scene.data, video_style)
        normalized_scene_video_path = str(current_scene_dir / "video.mp4")
        self._normalize_scene_video(video_path, normalized_scene_video_path, video_style)
        if Path(video_path).exists() and Path(video_path).resolve() != Path(normalized_scene_video_path).resolve():
            try:
                if str(video_path).startswith("/tmp/"):
                    Path(video_path).unlink()
            except OSError:
                pass

        self._ensure_scene_preview_image(current_scene.data, normalized_scene_video_path, current_scene_dir)

        # Persist the newly generated video details on the current scene
        current_scene.video_file_path = normalized_scene_video_path
        scene_videos.append(normalized_scene_video_path)

        log(f"Scene created: {normalized_scene_video_path}")

        # Update state with current progress
        updated_state = {
            "scene_plan": scene_plan,
            "scene_videos": scene_videos,
            "current_scene_index": current_scene_index + 1,
            "messages": [AIMessage(content=f"Created scene: {current_scene.scene_id} - {normalized_scene_video_path}")]
        }
        
        # Check if we have more scenes to create
        if current_scene_index + 1 < len(scene_plan):
            # Continue to create next scene
            log(f"Continuing to next scene ({current_scene_index + 2}/{len(scene_plan)})")
            return Command(goto="create_scene", update=updated_state)
        else:
            # All scenes created, go to merge
            log("All scenes created, proceeding to merge")
            updated_state["messages"].append(AIMessage(content="All scenes created, proceeding to merge videos"))
            return Command(goto="merge_scenes", update=updated_state)
        
    async def merge_scenes_node(self, state: State) -> Dict[str, Any]:
        """Merge all scene videos into a final local video file."""
        log("Creating final video...")
        
        scene_videos = state.get("scene_videos", [])
        video_spec = state.get("video_spec")
        run_output_dir = state.get("run_output_dir")

        if not scene_videos:
            return {"messages": [AIMessage(content="Error: No scene videos to merge")]}
        
        if not video_spec:
            return {"messages": [AIMessage(content="Error: No video specification found")]}
        if not run_output_dir:
            return {"messages": [AIMessage(content="Error: No output directory found")]}
        
        try:
            final_video_path = str(Path(run_output_dir) / "final_video.mp4")

            log(f"Final video will be saved as: {final_video_path}")
            
            # If only one scene video, process it with faststart and return local final video
            if len(scene_videos) == 1:
                log("Only one scene video, processing it with faststart optimization")
                try:
                    # Process the single scene video with faststart
                    single_scene_path = scene_videos[0]
                    if os.path.exists(single_scene_path):
                        # Apply faststart optimization using ffmpeg
                        ffmpeg_single_cmd = [
                            "ffmpeg", "-y",
                            "-i", single_scene_path,  # Input video
                            "-c", "copy",  # Copy streams without re-encoding
                            "-movflags", "+faststart",  # Enable fast start for web playback
                            final_video_path
                        ]
                        
                        result = subprocess.run(ffmpeg_single_cmd, capture_output=True, text=True, timeout=60)
                        if result.returncode != 0:
                            # Fallback to simple copy if faststart fails
                            log("Faststart optimization failed, falling back to simple copy")
                            import shutil
                            shutil.copy2(single_scene_path, final_video_path)
                        
                        final_video_url = final_video_path

                        # Note: Cost task saving is handled in create_video() method after final_video_path is available

                        return {
                            "final_video_path": final_video_url,
                            "messages": [AIMessage(content=f"Video creation completed! Final video: {final_video_url}")]
                        }
                    else:
                        return {"messages": [AIMessage(content=f"Error: Single scene video file not found: {single_scene_path}")]}
                except Exception as e:
                    return {"messages": [AIMessage(content=f"Error processing single scene video: {str(e)}")]}
            
            # Scene videos are now local file paths, validate they exist
            local_video_paths = []
            
            for i, video_path in enumerate(scene_videos):
                if os.path.exists(video_path):
                    local_video_paths.append(video_path)
                else:
                    log(f"Warning: Video file not found: {video_path}")
                    continue
            
            if not local_video_paths:
                return {"messages": [AIMessage(content="Error: No valid scene videos found for merging")]}
            
            # Build ffmpeg command using filter_complex concat filter to avoid timestamp issues
            # This approach concatenates video and audio streams properly without timestamp problems
            ffmpeg_cmd = ["ffmpeg", "-y"]  # -y to overwrite output file
            
            # Add all input files
            for video_path in local_video_paths:
                ffmpeg_cmd.extend(["-i", video_path])
            
            # Build filter_complex string for concatenation
            n_videos = len(local_video_paths)
            filter_inputs = ""
            for i in range(n_videos):
                filter_inputs += f"[{i}:v][{i}:a]"
            
            filter_complex = f"{filter_inputs}concat=n={n_videos}:v=1:a=1[outv][outa]"
            
            # Complete ffmpeg command
            ffmpeg_cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "19",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-r", "30",
                "-movflags", "+faststart",  # Enable fast start for web playback
                final_video_path
            ])
            
            log(f"Running ffmpeg to merge {len(local_video_paths)} scene videos using filter_complex...")
            
            try:
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    raise Exception(f"FFmpeg merge failed: {result.stderr}")
                
            except subprocess.TimeoutExpired:
                raise Exception("FFmpeg timeout during video merging")
            except Exception as e:
                raise Exception(f"Error running FFmpeg: {str(e)}")
            
            # Check if final video was created successfully
            if not os.path.exists(final_video_path):
                raise Exception("Final video file was not created")
            
            final_video_url = final_video_path
            log(f"Final video created: {final_video_url}")

            # Note: Cost task saving is handled in create_video() method after final_video_path is available

            return {
                "final_video_path": final_video_url,
                "messages": [AIMessage(content=f"Video creation completed! Final video: {final_video_url}")]
            }
            
        except Exception as e:
            log(f"Error in merge_scenes_node: {e}")
            return {"messages": [AIMessage(content=f"Error creating final video: {str(e)}")]}
        
    async def create_video(
        self,
        requirement: str,
        duration: int = 300,
        resolution: str = "1920x1080",
        thread_id: str = None,
        output_path: str = "/tmp",
    ) -> Dict[str, Any]:
        """
        Create an educational video based on a requirement

        Args:
            requirement: The requirement to create the video
            duration: Target video duration in seconds (default: 300 = 5 minutes)
            resolution: Video resolution (default: "1920x1080")
            thread_id: Optional thread ID for conversation tracking
            output_path: Parent directory to save generated artifacts

        Returns:
            Dictionary containing final video path and metadata
        """
        if not thread_id:
            import uuid
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}
        run_output_dir = self._create_run_output_dir(output_path, thread_id)

        initial_state = {
            "requirement": requirement,
            "target_duration": duration,
            "resolution": resolution,
            "output_path": output_path,
            "run_output_dir": run_output_dir,
            "thread_id": thread_id,
            "current_scene_index": 0,
            "scene_videos": [],
            "messages": [HumanMessage(content=f"Create video for requirement: {requirement}")]
        }
        
        try:
            # Run the workflow
            final_state = None
            async for chunk in self.graph.astream(initial_state, config=config, stream_mode="updates"):
                log(f"Workflow chunk: {list(chunk.keys())}")
                final_state = chunk
            
            if not final_state:
                raise Exception("Workflow completed without final state")
            
            # Extract results from the final state
            result = {}
            
            '''
            for _, node_data in final_state.items():
                if isinstance(node_data, dict):
                    if 'final_video_path' in node_data:
                        result['final_video_path'] = node_data['final_video_path']
                    if 'video_spec' in node_data:
                        result['video_spec'] = node_data['video_spec']
            '''

            state = await self.graph.aget_state(config=config)
            # Access the values property of the StateSnapshot to get the actual state data
            state_values = state.values if state else {}
            result['final_video_path']  = state_values.get('final_video_path')
            result['video_spec']  = asdict(state_values.get('video_spec', {}))
            result['scene_videos'] = state_values.get('scene_videos', [])
            result['scene_plan'] = state_values.get('scene_plan', [])
            
            # Generate thumbnail and extract video metadata
            final_video_url = result['final_video_path']
            if final_video_url:
                try:
                    metadata = await self._extract_video_metadata_and_thumbnail(
                        final_video_url,
                        state_values.get('requirement'),
                        state_values.get('video_spec')
                    )
                    result.update(metadata)
                except Exception as e:
                    log(f"Warning: Failed to extract video metadata: {e}")

            try:
                self._write_audit_readme(run_output_dir, state_values)
            except Exception as e:
                log(f"Warning: Failed to write audit README: {e}")
                
            log(f"Video creation completed successfully")
            return result
            
        except Exception as e:
            # log crash stack trace
            
            log(traceback.format_exc())
            log(f"Error in create_video: {e}")
            raise Exception(f"Video creation failed: {str(e)}")

    def create_multiple_scene_video(
        self,
        requirement: str,
        target_duration: int = 60,
        resolution: str = "1080x1920",
        output_path: str = "/tmp",
    ) -> str:
        result = asyncio.run(
            self.create_video(
                requirement=requirement,
                duration=target_duration,
                resolution=resolution,
                output_path=output_path,
            )
        )
        return str(result.get("final_video_path") or "")
    
    async def _extract_video_metadata_and_thumbnail(self, video_url: str, requirement: str = None, video_spec = None) -> Dict[str, Any]:
        """
        Extract video metadata and generate thumbnail using ffprobe and ffmpeg

        Args:
            video_url: URL of the video to analyze
            requirement: Video creation requirement containing context
            video_spec: Video specification with title and description

        Returns:
            Dictionary containing video metadata and thumbnail URL
        """
        import tempfile
        import json
        import aiohttp
        
        # Prepare local/temporary path for analysis
        temp_video_path = None
        temp_thumbnail_path = None
        
        try:
            if os.path.exists(video_url):
                temp_video_path = video_url
            else:
                timeout = aiohttp.ClientTimeout(total=300, connect=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(video_url) as response:
                        if response.status == 200:
                            temp_video_path = f"/tmp/temp_video_{uuid.uuid4().hex}.mp4"
                            with open(temp_video_path, 'wb') as f:
                                f.write(await response.read())
                        else:
                            raise Exception(f"Failed to download video: {response.status}")
            
            # Extract video metadata using ffprobe
            ffprobe_cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams",
                temp_video_path
            ]
            
            result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise Exception(f"ffprobe failed: {result.stderr}")
            
            probe_data = json.loads(result.stdout)
            
            # Extract video stream information
            video_stream = None
            audio_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                elif stream.get('codec_type') == 'audio':
                    audio_stream = stream
            
            if not video_stream:
                raise Exception("No video stream found")
            
            # Extract metadata
            metadata = {
                'duration': int(float(probe_data['format'].get('duration', 0))),
                'size': int(probe_data['format'].get('size', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
            }
            
            # Generate thumbnail at 1 second mark using AI image generation
            thumbnail_url = await self._generate_ai_thumbnail(requirement, video_spec)
            metadata['thumbnail_url'] = thumbnail_url
            
            return metadata
            
        except Exception as e:
            log(f"Error extracting video metadata: {e}")
            raise
        finally:
            # Clean up temporary files
            if temp_video_path and os.path.exists(temp_video_path) and not (video_url and temp_video_path == video_url):
                os.remove(temp_video_path)
            if temp_thumbnail_path and os.path.exists(temp_thumbnail_path):
                os.remove(temp_thumbnail_path)
    
    async def _generate_ai_thumbnail(self, requirement: str = None, video_spec: VideoSpec = None) -> str:
        """
        Generate a contextual thumbnail using AI based on video requirement
        
        Args:
            requirement: Video creation requirement containing context
            video_spec: Video specification with title and description
            
        Returns:
            URL of the generated thumbnail
        """
        try:
            # Extract visual context from requirement text
            prompt = await self._build_thumbnail_prompt(requirement, video_spec)

            # Generate thumbnail image
            thumbnail_path = await generate_image_from_prompt(prompt, style='icon')
            if not thumbnail_path:
                raise Exception("Failed to generate thumbnail image")
            
            return thumbnail_path
            
        except Exception as e:
            log(f"Error generating AI thumbnail: {e}")
            raise
    
    async def _build_thumbnail_prompt(self, requirement: str = None, video_spec: VideoSpec = None) -> str:
        """
        Use AI to generate a contextual thumbnail prompt from requirement and video spec
        
        Args:
            requirement: Video creation requirement text
            video_spec: Video specification
            
        Returns:
            AI-generated prompt for thumbnail generation
        """
        try:
            # Build input for AI to generate thumbnail prompt
            prompt_request = "Please create an AI image-generation prompt for an EDUCATIONAL VIDEO COVER/THUMBNAIL.\n\n"
            
            if requirement:
                prompt_request += f"Original Video Creation Requirement: {requirement}\n\n"
                
            if video_spec and video_spec.title:
                prompt_request += f"Video Title: {video_spec.title}\n\n"
            if video_spec and video_spec.description:
                prompt_request += f"Video Description: {video_spec.description}\n\n"
                
            prompt_request +=  """Goals:
1) Reflect the subject clearly for the target audience and be visually appealing.
2) Use a clean, modern, professional design with bright, engaging educational colors.
3) Include relevant symbols/icons tied to the topic (max 3).
4) Ensure strong readability and click-worthiness.
Return ONLY the final image prompt (no extra lines)."""

            # Use the LLM to generate thumbnail prompt
            messages = [
                SystemMessage(content=
                    "You are an expert visual designer for educational video thumbnails. "
                    "OUTPUT: Return a SINGLE, fully specified image-generation prompt (no commentary). "
                    "MODEL BEHAVIOR: The prompt will be used with GPT-Image-1 / 4o Images. Be explicit and layout-aware. "
                    "REQUIREMENTS:\n"
                    "- Thumbnail aspect 1:1. Reserve safe areas (≈96px top for title bars, 180px bottom for subtitles).\n"
                    "- One clear focal subject; include at most 0–3 small icons; avoid clutter.\n"
                    "- If on-image text is needed, keep ≤3 words; provide exact wording + font family (with generic fallback), weight/size/color/placement; add subtle outline/shadow for legibility.\n"
                    "- Specify style, 3–5 color palette with high contrast; lighting/mood; POV/composition; foreground/midground/background and spacing so the subject stays inside the central 60%.\n"
                    "- Include a short NEGATIVE list (e.g., no watermarks, no extra text, no brand logos, no busy backgrounds).\n"
                    "CONSTRAINTS: Return only the final prompt string."
                ),
                HumanMessage(content=prompt_request)
            ]
            
            response = await self.llm.ainvoke(messages)

            thumbnail_prompt = response.content.strip()

            log(f"AI-generated thumbnail prompt: {thumbnail_prompt}")
            return thumbnail_prompt
            
        except Exception as e:
            log(f"Error generating AI thumbnail prompt: {e}")
            # Fallback to simple prompt
            return "Educational video thumbnail, clean modern design, bright engaging colors, professional educational style, eye-catching composition"


# Factory function for easy initialization
def create_video_creator() -> VideoCreatorWorkflow:
    """Create and return a configured video creator workflow"""
    return VideoCreatorWorkflow()
