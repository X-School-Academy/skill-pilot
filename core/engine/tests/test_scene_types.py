import os
import sys
import tempfile
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the modules to test
from workflow.scene_types.text_only import create_text_only_scene
from workflow.scene_types.bullet_list import create_bullet_list_scene
from workflow.scene_types.image import create_image_scene
from workflow.scene_types.image_with_caption import create_image_with_caption_scene
from workflow.scene_types.icon_grid import create_icon_grid_scene
from workflow.scene_types.mermaid_diagram import (
    MermaidRenderError,
    DEFAULT_MERMAID_BACKGROUND,
    DEFAULT_MERMAID_THEME,
    _normalize_mermaid_code,
    _set_svg_root_background,
    create_mermaid_diagram_scene,
    generate_mermaid_image_with_retry,
    generate_svg_from_mermaid,
)
from workflow.scene_types.code_snippet import create_code_snippet_scene
from workflow.scene_types.table import create_table_scene
from workflow.scene_types.split_screen import create_split_screen_scene
from workflow.scene_types.quiz import create_quiz_scene
from workflow.scene_types.definition import create_definition_scene
from workflow.scene_types.text_animation import create_text_animation_scene
from workflow.scene_types.narration_only import create_narration_only_scene
from workflow.VideoStyle import VideoStyle

use_service_mock = True  # Use service mocks for LLM and image generation

class TestSceneTypes:

    @pytest.fixture
    def default_style(self):
        """Create default VideoStyle for testing"""
        style =  VideoStyle(theme="kids")
        style.width = 1920
        style.height = 1080
        return style
    
    @pytest.fixture(scope="session")
    def scene_video_results(self):
        """Store scene video results for merge testing"""
        return []
    
    @pytest.fixture(autouse=True)
    def mock_remove_files(self):
        """Mock os.remove to prevent actual file deletion during tests."""
        # with patch('your_module.os.remove') as mock_remove:
        with patch('os.remove') as mock_remove:
            # Configure the mock to do nothing (just return None)
            mock_remove.return_value = None
            yield mock_remove

    @pytest.fixture(autouse=True)
    def mock_rmtree_files(self):
        with patch('shutil.rmtree') as mock_remove:
            mock_remove.return_value = None
            yield mock_remove

    @pytest.fixture(autouse=use_service_mock)
    def mock_services(self):
        """Mock remote/media services against the current shared scene helpers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_audio_path = os.path.join(tmpdir, "test_audio.wav")
            test_image_path = os.path.join(tmpdir, "test_image.png")

            print(f"remote mock cloud services: {test_audio_path}, {test_image_path} will be created for testing")

            # Create a minimal valid WAV file (44 bytes header + 1 second of silence)
            sample_rate = 44100  # 44.1 kHz
            duration = 1  # 1 second
            samples = sample_rate * duration
            
            # WAV file header for 1 second of silence
            wav_header = b'RIFF'
            wav_header += (36 + samples * 2).to_bytes(4, 'little')  # File size - 8
            wav_header += b'WAVE'
            wav_header += b'fmt '
            wav_header += (16).to_bytes(4, 'little')  # Format chunk size
            wav_header += (1).to_bytes(2, 'little')   # Audio format (PCM)
            wav_header += (1).to_bytes(2, 'little')   # Number of channels
            wav_header += sample_rate.to_bytes(4, 'little')  # Sample rate
            wav_header += (sample_rate * 2).to_bytes(4, 'little')  # Byte rate
            wav_header += (2).to_bytes(2, 'little')   # Block align
            wav_header += (16).to_bytes(2, 'little')  # Bits per sample
            wav_header += b'data'
            wav_header += (samples * 2).to_bytes(4, 'little')  # Data chunk size
            
            with open(test_audio_path, 'wb') as f:
                f.write(wav_header)
                # Write 1 second of silence (16-bit PCM)
                f.write(b'\x00\x00' * samples)

            with open(test_image_path, 'wb') as f:
                f.write(
                    base64.b64decode(
                        "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFElEQVR42mP8z/CfAQgwMaACUvkAnR4E+c4Xn/AAAAAASUVORK5CYII="
                    )
                )

            async def mock_generate_image(*args, **kwargs):
                return test_image_path

            async def mock_async_tts(*args, **kwargs):
                return test_audio_path

            mock_llm_class = MagicMock()
            mock_llm_instance = AsyncMock()
            mock_llm_instance.text_to_audio_file = AsyncMock(return_value=test_audio_path)
            mock_llm_instance.__aenter__.return_value = mock_llm_instance
            mock_llm_instance.__aexit__.return_value = None
            mock_llm_class.return_value = mock_llm_instance

            mock_workflow_llm = MagicMock()
            mock_workflow_llm.return_value.ainvoke = AsyncMock(
                return_value=MagicMock(content="graph TD\n    A[Start] --> B[End]")
            )

            patch_configs = {
                'image': [
                    'workflow.scene_types.image_with_caption.generate_image_from_prompt',
                    'workflow.scene_types.icon_grid.generate_image_from_prompt',
                ],
                'tts': [
                    'workflow.scene_types.shared.async_text_to_audio_file',
                ],
                'llm': [
                    'workflow.scene_types.shared.LLM',
                ],
                'mermaid': [
                    'workflow.scene_types.mermaid_diagram.WorkflowLLMAdapter',
                    'workflow.scene_types.mermaid_diagram.generate_svg_from_mermaid',
                    'workflow.scene_types.mermaid_diagram.capture_image',
                    'workflow.scene_types.mermaid_diagram.subprocess.run',
                ]
            }

            started_patches = []
            try:
                for key, targets in patch_configs.items():
                    for target in targets:
                        p = patch(target, create=True)
                        started_patch = p.start()
                        started_patches.append(p)

                        if key == 'image':
                            started_patch.side_effect = mock_generate_image
                        elif key == 'tts':
                            started_patch.side_effect = mock_async_tts
                        elif key == 'llm':
                            started_patch.side_effect = mock_llm_class
                        elif key == 'mermaid':
                            if target.endswith('WorkflowLLMAdapter'):
                                started_patch.side_effect = mock_workflow_llm
                            elif target.endswith('generate_svg_from_mermaid'):
                                started_patch.side_effect = AsyncMock(return_value='<svg style="background-color: white;"></svg>')
                            elif target.endswith('subprocess.run'):
                                def mock_mermaid_subprocess_run(cmd, *args, **kwargs):
                                    output_path = cmd[-1]
                                    with open(output_path, 'wb') as f:
                                        f.write(b'\x00\x00')
                                    return MagicMock(returncode=0, stderr="", stdout="")

                                started_patch.side_effect = mock_mermaid_subprocess_run
                            else:
                                started_patch.side_effect = AsyncMock(return_value=test_image_path)
                
                yield

            finally:
                for p in started_patches:
                    p.stop()

    # Test 1: Text Only Scene
    @pytest.mark.anyio
    async def test_create_text_only_scene(self, default_style, scene_video_results):
        """Test text-only scene creation"""
        scene_data = {
            "text": "Welcome to Python Programming!",
            "voice_over": "In this lesson, we'll learn the basics of Python programming language."
        }
        
        result = await create_text_only_scene(scene_data, default_style)
        # Should return a local file path now with UUID format
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Text only scene created at: {result}")

    # Test 2: Bullet List Scene
    @pytest.mark.anyio
    async def test_create_bullet_list_scene(self, default_style, scene_video_results):
        """Test bullet list scene creation"""
        scene_data = {
            "items": [
                "Our sense of space",
                "Our instinct for danger",
                "Our hand-eye coordination",
                "Our ability to navigate uncertainty",
                "Our ability to make decisions in complex environments",
                "Our intuition",
                "Our imagination",
                "Our social awareness",
                "Our feel for the real world"
            ],
            "voice_over": "Here are the four fundamental concepts in programming."
        }
        
        result = await create_bullet_list_scene(scene_data, default_style)
        # Should return a local file path now with UUID format
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert "bullet_list_scene_" in result
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Bullet list scene created at: {result}")

    # Test 3: Image Scene
    @pytest.mark.anyio
    async def test_create_image_scene(self, default_style, scene_video_results):
        """Test image-only scene creation"""
        scene_data = {
            "image_prompt": "A modern computer setup with multiple monitors showing code, professional lighting",
            "voice_over": "A well-organized development environment is crucial for productive programming."
        }
        
        result = await create_image_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Image only scene created at: {result}")

    # Test 4: Image with Caption Scene
    @pytest.mark.anyio
    async def test_create_image_with_caption_scene(self, default_style, scene_video_results):
        """Test image with caption scene creation"""
        scene_data = {
        "scene_type": "image_with_caption",
        "image_prompt": "A bright, friendly illustration of a large blue circle on a white background. In the foreground, the circle is shown with a dashed line from its center to the edge, labeled with a small 'r'. The color palette is cheerful: blues, whites, and soft yellows. The overall style is clean and cartoon-like, with the circle centered and the radius clearly visible. Middle ground shows a simple ruler next to the circle. Background is minimal and bright.",
        "text": "The radius is the distance from the center to the edge.",
        "voice_over": "First, let's look at the circle. The line from the center to the edge is called the radius. We use the radius to help calculate the area."
        }
        
        result = await create_image_with_caption_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Image with caption scene created at: {result}")

    # Test 5: Icon Grid Scene
    @pytest.mark.anyio
    async def test_create_icon_grid_scene(self, default_style, scene_video_results):
        """Test icon grid scene creation"""
        scene_data = {
            "icons": [
                {"image_prompt": "rocket launch icon representing fast performance", "text": "Fast Performance"},
                {"image_prompt": "lightbulb icon representing smart features", "text": "Smart Features"},
                {"image_prompt": "security lock icon representing secure system", "text": "Secure System"},
                {"image_prompt": "globe icon representing global reach", "text": "Global Reach"}
            ],
            "voice_over": "Our platform offers these key features that make it stand out."
        }
        
        result = await create_icon_grid_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Icon grid scene created at: {result}")

    # Test 6: Mermaid Diagram Scene
    @pytest.mark.anyio
    async def test_create_mermaid_diagram_scene(self, default_style, scene_video_results):
        """Test mermaid diagram scene creation"""
        scene_data = {
            "diagram_type": "flowchart",
            "description": "A flowchart showing data processing workflow with User Input flowing to Validation, then Processing, and finally Output",
            "text": "Data Processing Workflow",
            "voice_over": "This flowchart shows our data processing workflow from input to output."
        }
        
        result = await create_mermaid_diagram_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Mermaid diagram scene created at: {result}")

    @pytest.mark.anyio
    async def test_generate_mermaid_image_with_retry_includes_code_and_cli_error(self):
        """Retry Mermaid generation only for Mermaid CLI render errors."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            side_effect=[
                MagicMock(content='mindmap\n  root((AI Agent 核心要点))\n  child((Bad Root))'),
                MagicMock(content='mindmap\n  root((AI Agent 核心要点))\n    child((Fixed Child))'),
            ]
        )

        with patch(
            'workflow.scene_types.mermaid_diagram.WorkflowLLMAdapter',
            return_value=mock_llm,
        ), patch(
            'workflow.scene_types.mermaid_diagram.generate_svg_from_mermaid',
            new=AsyncMock(
                side_effect=[
                    MermaidRenderError(
                        'Failed to generate SVG: There can be only one root.',
                        mermaid_code='mindmap\n  root((AI Agent 核心要点))\n  child((Bad Root))',
                        cli_error='There can be only one root. No parent could be found for ("AI Agent 核心要点")',
                    ),
                    '<svg style="background-color: white;"></svg>',
                ]
            ),
        ):
            svg = await generate_mermaid_image_with_retry(
                'mindmap',
                'Show AI agent core points',
                '/tmp/mmdc',
                max_retries=3,
            )

        assert svg == '<svg style="background-color: white;"></svg>'
        assert mock_llm.ainvoke.await_count == 2

        retry_message = mock_llm.ainvoke.await_args_list[1].args[0][-1].content
        assert 'Current Mermaid code:' in retry_message
        assert 'AI Agent 核心要点' in retry_message
        assert 'Mermaid CLI error:' in retry_message
        assert 'There can be only one root.' in retry_message

    @pytest.mark.anyio
    async def test_generate_mermaid_image_with_retry_does_not_retry_non_render_errors(self):
        """Non-Mermaid CLI failures should fail immediately."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content='graph TD\nA --> B'))

        with patch(
            'workflow.scene_types.mermaid_diagram.WorkflowLLMAdapter',
            return_value=mock_llm,
        ), patch(
            'workflow.scene_types.mermaid_diagram.generate_svg_from_mermaid',
            new=AsyncMock(side_effect=Exception('Timeout while generating SVG from mermaid code')),
        ):
            with pytest.raises(Exception, match='Failed to generate mermaid diagram: Timeout while generating SVG from mermaid code'):
                await generate_mermaid_image_with_retry(
                    'flowchart',
                    'Show a simple graph',
                    '/tmp/mmdc',
                    max_retries=3,
                )

        assert mock_llm.ainvoke.await_count == 1

    @pytest.mark.anyio
    async def test_generate_svg_from_mermaid_preserves_render_errors(self):
        """Mermaid CLI render failures should bubble up as MermaidRenderError."""
        mock_result = MagicMock(
            returncode=1,
            stderr='Error: There can be only one root. No parent could be found for ("AI Agent 核心要点")',
            stdout='',
        )

        with patch(
            'workflow.scene_types.mermaid_diagram.subprocess.run',
            return_value=mock_result,
        ):
            with pytest.raises(MermaidRenderError, match='Failed to generate SVG: Error: There can be only one root.'):
                await generate_svg_from_mermaid(
                    'mindmap\n  root((AI Agent 核心要点))\n  child((Bad Root))',
                    '/tmp/mmdc',
                )

    def test_set_svg_root_background_preserves_child_styles(self):
        """Only the root svg tag should be rewritten for background color."""
        svg = (
            '<svg style="color: black;"><g>'
            '<text style="fill: red;">hello</text>'
            '</g></svg>'
        )

        updated = _set_svg_root_background(svg, "white")

        assert '<svg style="background-color: white;">' in updated
        assert '<text style="fill: red;">hello</text>' in updated

    @pytest.mark.anyio
    async def test_generate_svg_from_mermaid_passes_theme_and_background(self):
        """Mermaid CLI should be called with an explicit readable theme."""
        mock_result = MagicMock(
            returncode=0,
            stderr='',
            stdout='<svg><text style="fill: red;">hello</text></svg>',
        )

        with patch(
            'workflow.scene_types.mermaid_diagram.subprocess.run',
            return_value=mock_result,
        ) as mock_run:
            svg = await generate_svg_from_mermaid('graph TD\nA-->B', '/tmp/mmdc')

        cmd = mock_run.call_args.args[0]
        assert cmd == [
            '/tmp/mmdc',
            '-i',
            '-',
            '-e',
            'svg',
            '-o',
            '-',
            '-t',
            DEFAULT_MERMAID_THEME,
            '-b',
            DEFAULT_MERMAID_BACKGROUND,
        ]
        assert '<svg style="background-color: white;">' in svg
        assert '<text style="fill: red;">hello</text>' in svg

    def test_normalize_mermaid_code_strips_fences_duplicates_and_mindmap_root(self):
        """Normalization should clean common LLM formatting mistakes before Mermaid CLI."""
        raw_code = """```mermaid
mindmap
  root((AI Agent 核心要点))
    什么是AI Agent
      装了工具的AI
```
mindmap
  root((AI Agent 核心要点))
    能做什么
      读写文件
"""

        normalized = _normalize_mermaid_code(raw_code, 'mindmap')

        assert normalized == (
            "mindmap\n"
            "  root((AI Agent 核心要点))\n"
            "    什么是AI Agent\n"
            "      装了工具的AI"
        )

    @pytest.mark.anyio
    async def test_generate_mermaid_image_with_retry_normalizes_llm_output_before_render(self):
        """Retry pipeline should sanitize Mermaid before handing it to the CLI."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="""```mermaid
mindmap
  root((AI Agent 核心要点))
    什么是AI Agent
      装了工具的AI
```
mindmap
  root((AI Agent 核心要点))
    能做什么
      读写文件
"""
            )
        )

        mock_render = AsyncMock(return_value='<svg style="background-color: white;"></svg>')

        with patch(
            'workflow.scene_types.mermaid_diagram.WorkflowLLMAdapter',
            return_value=mock_llm,
        ), patch(
            'workflow.scene_types.mermaid_diagram.generate_svg_from_mermaid',
            new=mock_render,
        ):
            svg = await generate_mermaid_image_with_retry(
                'mindmap',
                'Show AI agent core points',
                '/tmp/mmdc',
                max_retries=3,
            )

        assert svg == '<svg style="background-color: white;"></svg>'
        assert mock_render.await_args.args[0] == (
            "mindmap\n"
            "  root((AI Agent 核心要点))\n"
            "    什么是AI Agent\n"
            "      装了工具的AI"
        )

    def test_normalize_mermaid_code_cuts_inline_duplicate_diagram_keyword(self):
        """If the model appends another diagram without a newline, keep only the first one."""
        raw_code = (
            "mindmap\n"
            "  AI Agent 核心要点\n"
            "    学习平台mindmap\n"
            "  root((Second Diagram))\n"
            "    Ignore Me"
        )

        normalized = _normalize_mermaid_code(raw_code, 'mindmap')

        assert normalized == (
            "mindmap\n"
            "  root((AI Agent 核心要点))\n"
            "    学习平台"
        )

    # Test 7: Code Snippet Scene
    @pytest.mark.anyio
    async def test_create_code_snippet_scene(self, default_style, scene_video_results):
        """Test code snippet scene creation"""
        scene_data = {
            "code": "```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n```",
            "voice_over": "This Python function calculates the Fibonacci sequence using recursion."
        }
        
        result = await create_code_snippet_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Code snippet scene created at: {result}")

    # Test 8: Table Scene
    @pytest.mark.anyio
    async def test_create_table_scene(self, default_style, scene_video_results):
        """Test table scene creation"""
        scene_data = {
            "rows": [
                ["Language", "Year Created", "Primary Use"],
                ["Python", "1991", "Data Science, Web Development"],
                ["JavaScript", "1995", "Web Development"],
                ["Java", "1995", "Enterprise Applications"],
                ["C++", "1985", "System Programming"]
            ],
            "text": "Programming Languages Comparison",
            "voice_over": "Here's a comparison of popular programming languages and their characteristics."
        }
        
        result = await create_table_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Table scene created at: {result}")

    # Test 9: Split Screen Scene
    @pytest.mark.anyio
    async def test_create_split_screen_scene(self, default_style, scene_video_results):
        """Test split screen scene creation"""
        scene_data = {
            "text1": """\
**Thought HARDEST:**

- Math
- Coding
- Academic writing
- Standardized problem-solving

Actually most reproducible by AI
""",
            "text2": """\
**Thought SIMPLE:**
- Perception
- Intuition
- Embodied action
- Creativity
- Real-world judgment

Actually hardest to copy
""",
            "voice_over": "Let's compare poorly written code with clean, maintainable code."
        }
        
        result = await create_split_screen_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Split screen scene created at: {result}")

    # Test 10: Quiz Scene
    @pytest.mark.anyio
    async def test_create_quiz_scene(self, default_style, scene_video_results):
        """Test quiz scene creation"""
        scene_data = {
            "question": "Which of the following is a correct way to define a function in Python?",
            "options": [
                "def my_function():",
                "function my_function():",
                "func my_function():",
                "define my_function():"
            ],
            "answer": 0,
            "question_voice_over": "Let's test your knowledge of Python function syntax.",
            "answer_voice_over": "Correct! In Python, functions are defined using the 'def' keyword."
        }
        
        result = await create_quiz_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Quiz scene created at: {result}")

    # Test 11: Definition Scene
    @pytest.mark.anyio
    async def test_create_definition_scene(self, default_style, scene_video_results):
        """Test definition scene creation with markdown, code highlighting, and KaTeX"""
        scene_data = {
            "term": "Circle Area Calculation",
            "definition": """
## Mathematical Formula

The area of a circle is calculated using the formula:

$$A = \\pi r^2$$

Where:
- $A$ is the area
- $\\pi$ (pi) ≈ 3.14159
- $r$ is the radius

## Python Implementation

Here's how to calculate a circle's area in Python:

```python
import math

def calculate_circle_area(radius):
    \"\"\"
    Calculate the area of a circle given its radius.
    
    Args:
        radius (float): The radius of the circle
        
    Returns:
        float: The area of the circle
    \"\"\"
    if radius < 0:
        raise ValueError("Radius cannot be negative")
    
    area = math.pi * radius ** 2
    return area

# Example usage
radius = 5.0
area = calculate_circle_area(radius)
print(f"Circle with radius {radius} has area: {area:.2f}")
```

""",
            "voice_over": "Let's learn how to calculate the area of a circle using both mathematical formulas and Python code. The formula uses pi times radius squared, and we can implement this efficiently in Python using the math library."
        }
        
        result = await create_definition_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Definition scene created at: {result}")

    # Test 12: Text Animation Scene
    @pytest.mark.anyio
    async def test_create_text_animation_scene(self, default_style, scene_video_results):
        """Test text animation scene creation"""
        scene_data = {
            "scene_type": "text_animation",
            "animation_type": "typewriter",
            "text": "Finding the Area of a Circle: A Simple Guide",
            "voice_over": "Welcome! Today, we'll learn how to find the area of a circle using a simple formula."
        }
        
        result = await create_text_animation_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Text animation scene created at: {result}")

    # Test 13: Narration Only Scene
    @pytest.mark.anyio
    async def test_create_narration_only_scene(self, default_style, scene_video_results):
        """Test narration-only scene creation"""
        scene_data = {
            "voice_over": "This concludes our introduction to Python programming. Practice these concepts to master the fundamentals."
        }
        
        result = await create_narration_only_scene(scene_data, default_style)
        # Should return a local file path now
        assert result.startswith("/tmp/")
        assert result.endswith(".mp4")
        assert os.path.exists(result)
        
        # Store result for merge test
        scene_video_results.append(result)
        print(f"Narration scene created at: {result}")

    # Test 14: Merge Scenes Node - Using collected results from scene tests
    @pytest.mark.anyio
    async def test_merge_scenes_node_with_collected_results(self, scene_video_results):
        """Test merge_scenes_node function using State Manipulation with collected scene videos"""
        # Import the VideoCreatorWorkflow to test merge_scenes_node
        from workflow.video_creator import VideoCreatorWorkflow, VideoSpec
        
        # Ensure we have collected some scene videos from previous tests
        assert len(scene_video_results) > 0, "No scene videos collected from previous tests"

        if len(scene_video_results) < 2:
            pytest.skip("less then 2 videos collected from previous tests, skipping merge test")
        
        print(f"Testing merge_scenes_node with {len(scene_video_results)} collected videos...")
        for i, video_path in enumerate(scene_video_results):
            print(f"Video {i+1}: {video_path}")
        
        # Create video creator workflow instance
        workflow = VideoCreatorWorkflow()
        
        # Create a mock video spec
        video_spec = VideoSpec(
            knowledge_point="Python Programming Complete Course",
            duration=60,
            resolution="1080x1920",
            title="Complete Python Course from Multiple Scenes",
            description="A complete Python programming course merged from different scene types",
            target_audience="Programming beginners",
            learning_objectives=["Master Python basics", "Understand core concepts", "Write efficient code"]
        )
        
        # Create state with collected scene videos (State Manipulation)
        state = {
            "scene_videos": scene_video_results,
            "video_spec": video_spec,
            "messages": []
        }
        
        # Test merge_scenes_node using State Manipulation
        result = await workflow.merge_scenes_node(state)
        
        # Verify the result
        assert "final_video_path" in result
        assert result["final_video_path"] is not None
        assert "messages" in result
        assert len(result["messages"]) > 0
        
        # The final video should now use UUID format and be uploaded to S3
        final_video_path = result["final_video_path"]
        print(f"Final merged video: {final_video_path}")
        
        # Verify success message
        success_msg = result["messages"][-1]
        assert "successfully" in success_msg.lower()

    @pytest.mark.anyio
    async def test_gemini_tts_integration(self):
        """Test Gemini TTS integration with voice mapping"""
        # This test will mock the Gemini TTS but verify the voice mapping logic
        
        # Test voice mapping from OpenAI voices to Gemini voices
        from gemini_tts import async_text_to_audio_file
        
        # Mock environment variable
        with patch.dict(os.environ, {'GOOGLEAI_API_KEY': 'test_key'}):
            with patch('gemini_tts.text_to_audio_file') as mock_gemini_tts, \
                    patch('gemini_tts.save_cost_event', new_callable=AsyncMock) as mock_save_cost_event, \
                    patch('gemini_tts.calculate_tts_cost', return_value=0.1234):
                mock_gemini_tts.return_value = "/tmp/test_gemini_audio.wav"

                # Test voice mapping
                audio_path, cost = await async_text_to_audio_file("Test text", voice="alloy")

                # Verify the function was called (voice should be mapped to Kore)
                mock_gemini_tts.assert_called_once()
                args = mock_gemini_tts.call_args[0]
                mapped_voice = args[1]  # Second argument should be the mapped voice

                # alloy should map to Kore
                assert mapped_voice == "Kore"
                assert audio_path == "/tmp/test_gemini_audio.wav"
                assert cost == pytest.approx(0.1234)
                mock_save_cost_event.assert_awaited_once()

                print(f"Voice mapping test passed: alloy -> {mapped_voice}")
