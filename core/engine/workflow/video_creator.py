import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Literal, Annotated
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
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

# Import cost tracking functions
from ai_cost_config import save_cost_event, save_cost_task
from image_service import generate_image_from_prompt
from .llm_adapter import WorkflowLLMAdapter

AZURE_CHAT_MODEL_NAME = os.getenv("AZURE_OPENAI_CHAT_MODEL_NAME", "gpt-4o")

# Import VideoStyle from separate module to avoid circular imports
from .VideoStyle import VideoStyle

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

    # Cost tracking parameters
    cost_member_id: Optional[int]  # None for predefined courses, member_id for customized
    total_cost: float  # Accumulated cost for this video creation

    # Workflow state
    video_spec: Optional[VideoSpec]
    video_style: Optional[VideoStyle]  # Shared style configuration for all scenes
    scene_plan: Optional[List[Scene]]
    scene_videos: List[str]  # List of generated scene video file paths
    final_video_path: Optional[str]

    # Processing state
    current_scene_index: int
    total_scenes: int


class VideoCreatorWorkflow:
    """LangGraph workflow for creating educational videos"""

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

            # Track cost for this LLM call
            total_cost = state.get("total_cost", 0.0)
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                if usage:
                    event = await save_cost_event(
                        provider="azure_openai",
                        model=AZURE_CHAT_MODEL_NAME,
                        cost_type="text",
                        scope_id=state.get("cost_member_id") or 0,
                        note="Video specification design",
                        input_tokens=usage.get('prompt_tokens', 0),
                        output_tokens=usage.get('completion_tokens', 0)
                    )
                    if event and 'data' in event:
                        total_cost += event['data'].get('total_cost', 0.0)

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
                "total_cost": total_cost,
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

## Supported Scene Types

Below are the available scene types you can use. Each scene type must follow the structure exactly as shown. Use them strategically to explain the knowledge point.

* Text Only – Single line of highlighted text, ideal for emphasising a key term or concept. It will be put in the middle of the screen, for long text, it should be auto wrap and left align
```json
{{
  "scene_type": "text_only",
  "text": "string - shown in the screen",
  "voice_over": "string"
}}
```

* Bullet List – Multiple bullet points, for listing definitions, steps, or features. The list should be in the middle of the screen, and the string list items are left align and auto wrap for long item.
```json
{{
  "scene_type": "bullet_list",
  "items": ["string - item text shown in the screen"],
  "voice_over": "string"
}}
```

* Image – Full-screen static image or illustration without overlaid text.
```json
{{
  "scene_type": "image",
  "image_prompt": "string - AI prompt which will be used to create the image",
  "voice_over": "string"
}}
```

* Image With Caption – Static image with a short descriptive caption. The caption is in the bottom of the image with a line height margin on the top.
```json
{{
  "scene_type": "image_with_caption",
  "image_prompt": "string - AI prompt which will be used to create the image",
  "text": "string - caption of the image",
  "voice_over": "string"
}}
```

* Icon Grid – Multiple small icons or illustrations arranged in a grid, each representing an idea, max 4 icons per scene. For each icon, the text will be under the icon.
```json
{{
  "scene_type": "icon_grid",
  "icons": [
    {{
      "image_prompt": "string - use to create the icon image with AI",
      "text": "string - the caption of the image"
    }}
  ],
  "voice_over": "string"
}}
```

* Mermaid Diagram – Use Mermaid syntax to render flowcharts, sequence diagrams, etc. We do only support type: `flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`,`erDiagram`, `pie`, `mindmap` and `timeline`
```json
{{
  "scene_type": "mermaid_diagram",
  "diagram_type": "flowchart, sequenceDiagram, classDiagram, stateDiagram-v2, erDiagram, pie, mindmap or timeline",
  "description": "string - the detail of the diagram, which we will use AI to create the mermaid diagram code",
  "text": "string - caption of the diagram",
  "voice_over": "string"
}}
```

* Code Snippet – A formatted code block with syntax highlighting for a specific programming language.
```json
{{
  "scene_type": "code_snippet",
  "language": "string - programming language for syntax highlighting, e.g., 'python', 'javascript'",
  "code": "Markdown code block — enclosed by three backticks, ideally no more than 7 lines",
  "voice_over": "The text for voice-over to explain the code snippet for the knowledge point."
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
  "voice_over": "The text for voice-over."
}}
```

* Split-Screen – Two short string items shown side-by-side for direct comparison.
```json
{{
  "scene_type": "split_screen",
  "text1": "string",
  "text2": "string",
  "voice_over": "The text for voice-over."
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
  "voice_over": "The text for voice-over."
}}
```

* Text Animation – Pure text animated for a short text with html5/css, we will only support type: 'fade-in', 'slide-in' ,'typewriter', 'blink' or 'scale-up'
This scene type is ideal for emphasizing titles, key points, or important concepts. Ensure the voice-over duration matches or slightly exceeds the animation duration for a smooth and synchronized experience.
```json
{{
  "scene_type": "text_animation",
  "animation_type": "string: 'fade-in', 'slide-in' ,'typewriter', 'blink' or 'scale-up'",
  "text": "string - the text for animation",
  "voice_over": "The text for voice-over."
}}
```

* Narration Only –  Audio narration with a static background (no visuals or text).
```json
{{
  "scene_type": "narration_only",
  "voice_over": "The text for voice-over."
}}
```

Return your full video plan as a JSON object:

{{
    "scenes": [
        {{
            "scene_type": "text_only",
            "text": "string - shown in the screen",
            "voice_over": "string"
        }},
        {{
            "scene_type": "bullet_list",
            "items": ["string - item text"],
            "voice_over": "string"
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

            # Track cost for this LLM call
            total_cost = state.get("total_cost", 0.0)
            if hasattr(response, 'response_metadata'):
                usage = response.response_metadata.get('token_usage', {})
                if usage:
                    event = await save_cost_event(
                        provider="gemini",
                        model="gemini-2.0-flash",
                        cost_type="text",
                        scope_id=state.get("cost_member_id") or 0,
                        note="Video scene planning",
                        input_tokens=usage.get('prompt_tokens', 0),
                        output_tokens=usage.get('completion_tokens', 0)
                    )
                    if event and 'data' in event:
                        total_cost += event['data'].get('total_cost', 0.0)

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
                "total_cost": total_cost,
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
        cost_member_id: Optional[int] = None
    ) -> tuple[str, float]:
        """
        Create a scene video based on the scene type.
        This function calls the appropriate scene type module to generate the video.

        Args:
            scene: Scene data dictionary containing scene_type and all scene-specific data
            style: Video style configuration for consistent styling
            cost_member_id: Member ID for cost tracking (None for system cost)

        Returns:
            tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
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
        }
        
        # Get the appropriate scene creator function
        creator_func = scene_creators.get(scene_type)
        if not creator_func:
            raise ValueError(f"Unsupported scene type: {scene_type}")
        
        # Call the scene creator function with scene data, style configuration, and cost tracking
        try:
            video_url, scene_cost = await creator_func(scene, style, cost_member_id)
            return video_url, scene_cost
        except Exception as e:
            error(f"Error creating {scene_type.value} scene: {e}")
            raise Exception(f"Failed to create scene of type {scene_type.value}: {str(e)}")
    
    async def create_scene_node(self, state: State) -> Command[Literal["create_scene", "merge_scenes"]]:
        """Create a scene with video URL and decide next step"""
        scene_plan = state.get("scene_plan", [])
        current_scene_index = state.get("current_scene_index", 0)
        scene_videos = state.get("scene_videos", [])
        video_style = state.get("video_style")
        cost_member_id = state.get("cost_member_id")
        total_cost = state.get("total_cost", 0.0)

        if not scene_plan:
            raise ValueError("No scene plan found in state")

        if not video_style:
            raise ValueError("No video style configuration found in state")

        if current_scene_index >= len(scene_plan):
            raise ValueError("Scene index out of range")

        current_scene = scene_plan[current_scene_index]

        log(f"Creating scene {current_scene_index + 1}/{len(scene_plan)}: {current_scene.scene_id}")

        # Generate video file path using scene type-specific creator with style and cost tracking
        video_path, scene_cost = await self.create_scene_video_by_type(current_scene.data, video_style, cost_member_id)

        # Update total cost with scene cost
        total_cost += scene_cost
        if scene_cost > 0:
            log(f"Scene {current_scene.scene_id} cost: ${scene_cost:.4f}, Total cost so far: ${total_cost:.4f}")

        # Persist the newly generated video details on the current scene
        current_scene.video_file_path = video_path
        scene_videos.append(video_path)

        log(f"Scene created: {video_path}")

        # Update state with current progress and accumulated cost
        updated_state = {
            "scene_plan": scene_plan,
            "scene_videos": scene_videos,
            "current_scene_index": current_scene_index + 1,
            "total_cost": total_cost,
            "messages": [AIMessage(content=f"Created scene: {current_scene.scene_id} - {video_path}")]
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
        
        if not scene_videos:
            return {"messages": [AIMessage(content="Error: No scene videos to merge")]}
        
        if not video_spec:
            return {"messages": [AIMessage(content="Error: No video specification found")]}
        
        try:
            # Generate a unique UUID for the final video filename
            unique_id = str(uuid.uuid4())
            final_video_filename = f"{unique_id}.mp4"
            final_video_path = f"/tmp/{final_video_filename}"

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
        
        finally:
            # Clean up temporary files
            try:
                # Keep final output file; only cleanup intermediate scene files.
                if 'local_video_paths' in locals():
                    for path in local_video_paths:
                        if os.path.exists(path):
                            os.remove(path)
            except:
                pass  # Ignore cleanup errors
    
    async def create_video(
        self,
        requirement: str,
        duration: int = 300,
        resolution: str = "1920x1080",
        thread_id: str = None,
        category: str = "predefined-course",  # "predefined-course" or "customized-course"
        member_id: Optional[int] = None  # Required for customized-course
    ) -> Dict[str, Any]:
        """
        Create an educational video based on a requirement

        Args:
            requirement: The requirement to create the video
            duration: Target video duration in seconds (default: 300 = 5 minutes)
            resolution: Video resolution (default: "1920x1080")
            thread_id: Optional thread ID for conversation tracking
            category: Course category - "predefined-course" or "customized-course"
            member_id: Member ID for cost tracking (required for customized-course)

        Returns:
            Dictionary containing final video path and metadata
        """
        if not thread_id:
            import uuid
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}

        # For predefined courses: cost_member_id=None (system cost)
        # For customized courses: cost_member_id=member_id (member cost)
        cost_member_id = None if category == "predefined-course" else member_id

        initial_state = {
            "requirement": requirement,
            "target_duration": duration,
            "resolution": resolution,
            "thread_id": thread_id,
            "current_scene_index": 0,
            "scene_videos": [],
            "cost_member_id": cost_member_id,
            "total_cost": 0.0,
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
            result['total_cost'] = state_values.get('total_cost', 0.0)
            
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
                
                # Save cost task using final_video_url (which is the S3 URL from final_video_path)
                total_cost = state_values.get('total_cost', 0.0)
                if total_cost > 0:
                    try:
                        await save_cost_task("course_video", final_video_url, total_cost)
                        log(f"Saved cost tracking for video {final_video_url}: ${total_cost:.4f}")
                    except Exception as e:
                        log(f"Error saving cost task: {e}")
            
            log(f"Video creation completed successfully")
            return result
            
        except Exception as e:
            # log crash stack trace
            
            log(traceback.format_exc())
            log(f"Error in create_video: {e}")
            raise Exception(f"Video creation failed: {str(e)}")

    def create_course_video(self, requirement: str, target_duration: int = 60, resolution: str = "1080x1920") -> str:
        result = asyncio.run(
            self.create_video(
                requirement=requirement,
                duration=target_duration,
                resolution=resolution,
                category="predefined-course",
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
            thumbnail_path, _ = await generate_image_from_prompt(prompt, style='icon')
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

            # Note: Thumbnail prompt generation happens after video creation is complete,
            # so we don't track this cost to the video creation task
            # This is a post-processing step for metadata generation

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

# Convenience function for external use
async def create_video_by_knowledgepoint(
    course_pid: str,
    section_pid: str,
    knowledge_pid: str,
    requirement: str,
    category: str = "predefined-course",  # "predefined-course" or "customized-course"
    member_id: Optional[int] = None  # Required for customized-course
) -> str:
    """
    Create a video for a specific knowledge point and save to course-content collection

    Args:
        course_pid: Course parent ID
        section_pid: Section parent ID
        knowledge_pid: Knowledge point parent ID
        requirement: Detailed video creation requirement with all context
        category: Course category - "predefined-course" or "customized-course"
        member_id: Member ID for cost tracking (required for customized-course)

    Returns:
        Video URL from the created course-content record
    """
    try:
        # Import CMS for database operations
        from strapi4.cms import CMS
        from strapi4 import flatten_strapi_object

        cms = CMS()

        # Create video creator workflow with proper cleanup
        async with create_video_creator() as creator:
            # Create video with appropriate duration and resolution
            result = await creator.create_video(
                requirement=requirement,
                duration=60,  # 60 seconds for knowledge videos
                resolution="1080x1920",  # Mobile-first vertical format
                category=category,
                member_id=member_id
            )
        
        video_url = result.get('final_video_path')
        if not video_url:
            raise Exception("No video URL returned from creator")
        
        # Prepare metadata for course-content.data field
        metadata = {
            'meta': {
                'thumbnail_url': result.get('thumbnail_url'),
                'duration': result.get('duration'),
                'size': result.get('size'), 
                'width': result.get('width'),
                'height': result.get('height')
            },
            'video_spec': result.get('video_spec', {}),
            'scenes': []
        }
        
        # Add scene data to metadata
        scene_plan = result.get('scene_plan', [])
        for scene in scene_plan:
            scene_data = {
                'scene_id': scene.scene_id,
                'scene_type': scene.data.get('scene_type'),
                'data': scene.data
            }
            metadata['scenes'].append(scene_data)
        
        # Save to course-content collection
        course_content_data = {
            'type': 'knowledge_video',
            'course_uid': course_pid,
            'section_uid': section_pid, 
            'knowledge_uid': knowledge_pid,
            'url': video_url,
            'data': metadata
        }
        
        # Create the course-content record
        await cms.create_collection_record('course-content', course_content_data)
        
        log(f"Created course-content record for video: {video_url}")
        return video_url
        
    except Exception as e:
        log(f"Error in create_video function: {e}")
        raise Exception(f"Failed to create video for knowledge point: {str(e)}")
