#!/usr/bin/env python3
import os

from logger import log
from course_manager import update_node_version
from strapi4 import flatten_strapi_object
from strapi4.cms import CMS
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import Pydantic BaseModel for structured responses
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from langgraph.managed.is_last_step import RemainingSteps
from json_repair import repair_json
import traceback

from image_service import generate_image_from_prompt
from .llm_adapter import AgentCliLLMAdapter


@dataclass
class KnowledgePoint:
    name: str
    description: str
    keywords: List[str]
    content: str


@dataclass
class KnowledgePointDraft:
    name: str


@dataclass
class Section:
    name: str
    description: str
    knowledge_points: List[KnowledgePoint]


@dataclass
class SectionDraft:
    name: str
    description: str
    knowledge_points: List[KnowledgePointDraft]


@dataclass
class CourseDraft:
    name: str
    description: str
    sections: List[SectionDraft]
    subheading: str = ""
    language: str = "English"
    assignment_requirement: str = "General"
    video_requirement: str = "General"
    subject: str = "Learning"


@dataclass
class CourseDetails:
    name: str
    description: str
    sections: List[Section]
    subheading: str = ""
    language: str = "English"
    assignment_requirement: str = "General"
    video_requirement: str = "General"
    subject: str = "Learning"


class State(TypedDict):
    # Messages have the type "list". The add_messages function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: List[Any]
    # keeps track of the number of steps remaining until reaching the recursion limit
    remaining_steps: RemainingSteps
    thread_id: str
    course_draft: Optional[CourseDraft]
    course_details: Optional[CourseDetails]
    draft_iteration: int
    structured_response: Optional[Any]
    # Batch processing state
    current_batch_index: int
    total_batches: int
    detailed_sections: List[Section]
    thumbnail_url: Optional[str]
    language: str


def _init_checkpointer():
    return MemorySaver()


memory = _init_checkpointer()


class PredefinedCoursePlannerWorkflow:
    def __init__(self):
        self.max_retries = 3
        self.max_draft_iterations = 1  # No iteration needed for predefined courses
        self.max_sections_per_batch = 5
        self.recursion_limit = 20

        # Initialize LLM
        self.llm = self._init_llm()

        # Build workflow graph
        self.graph = self._build_graph()

    async def __aenter__(self) -> "PredefinedCoursePlannerWorkflow":
        """Allow usage as an async context manager for predictable teardown."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self.close()
        return False

    async def close(self) -> None:
        """Release LLM networking resources before shutting down."""
        try:
            llm_client = getattr(self.llm, 'async_client', None)
            if llm_client and hasattr(llm_client, 'aclose'):
                await llm_client.aclose()
                self.llm = None
        except Exception as err:  # pylint: disable=broad-except
            log(f"Error closing PredefinedCoursePlannerWorkflow resources: {err}")

    def _init_llm(self):
        """Initialize the LLM model based on environment configuration"""
        return AgentCliLLMAdapter()

    def _build_graph(self) -> StateGraph:
        """Build the workflow graph with nodes and edges"""
        workflow = StateGraph(State)

        # Add nodes - simplified workflow without interrupts
        workflow.add_node("course_drafter", self.course_drafter_node)
        workflow.add_node("course_creator_init", self.course_creator_init_node)
        workflow.add_node("course_creator", self.course_creator_node)
        workflow.add_node("thumbnail_generator", self.thumbnail_generator_node)

        # Add edges - direct flow without interrupts
        workflow.add_edge(START, "course_drafter")
        workflow.add_edge("course_drafter", "course_creator_init")
        workflow.add_edge("course_creator_init", "course_creator")
        workflow.add_conditional_edges(
            "course_creator",
            self.route_course_creator,
            {
                "course_creator": "course_creator",
                "generate_thumbnail": "thumbnail_generator"
            }
        )
        workflow.add_edge("thumbnail_generator", END)

        # Compile with memory
        return workflow.compile(checkpointer=memory)

    async def course_drafter_node(self, state: State) -> Dict[str, Any]:
        """Create course draft based on request message"""
        log(f"Predefined Course Drafter - Creating draft")

        # Get the language parameter passed to start_workflow
        language = state.get('language', 'English')

        draft_system_prompt = """\
You are an expert course design assistant for creating predefined courses. Create a comprehensive and well-structured course plan based on the given request.

Your task:
- Generate a well-defined course name and a short description outlining the course objectives.
- Create a compelling subheading that serves as a tagline or brief summary of what students will achieve.
- Organize the course into multiple sections, each focusing on a distinct topic or skill area.
- For each section, list clear and concise knowledge points (in bullet list format).
- Assume we will deliver **one knowledge point per day**. For example, a course with 30 knowledge points will span 30 days.
- Create content suitable for a general audience who might enroll in this predefined course.
- The course should be in the specified language: {language}
- Set assignment_requirement and video_requirement to "General" unless specific requirements are mentioned

Requirements:
- Make the plan suitable for AI-powered wide learning: focus on covering broad and essential knowledge rather than deep specialization.
- Be practical and structured, as this will guide a daily learning app.
- Create comprehensive content that would be valuable for anyone interested in the subject.
- Ensure all course content (name, description, sections, knowledge points) are in {language}.

Output format:
Return the course plan as a JSON object in this **exact format**:

{{
    "name": "Course name",
    "description": "Brief description of the course and its learning objectives.",
    "subheading": "Compelling tagline or brief summary of what students will achieve",
    "assignment_requirement": "General",
    "video_requirement": "General",
    "subject": "Learning topic or subject area",
    "sections": [
        {{
            "name": "Section Name", 
            "description": "Overview of what this section will teach.",
            "knowledge_points": ["Point 1", "Point 2", "Point 3"]
        }}
    ]
}}
"""

        system_message = SystemMessage(
            content=draft_system_prompt.format(language=language))

        # Get the request message from state
        messages = state.get('messages', [])
        if not messages:
            raise ValueError("Request message is required")

        human_message = messages[0]  # The request message
        current_messages = [system_message, human_message]

        response = await self.llm.ainvoke(current_messages, config={
            "configurable": {
                "model_kwargs": {"response_format": {"type": "json_object"}}
            }
        })

        # Add AI response to messages
        messages.append(response)

        # Strip whitespace and newlines from response content before parsing
        content = response.content.strip()
        content = repair_json(content)  # Repair any JSON formatting issues
        draft_data = json.loads(content)
        course_draft = CourseDraft(
            name=draft_data["name"],
            description=draft_data["description"],
            subheading=draft_data.get("subheading", ""),
            language=language,
            assignment_requirement=draft_data.get(
                "assignment_requirement", "General"),
            video_requirement=draft_data.get("video_requirement", "General"),
            subject=draft_data.get("subject", "Learning"),
            sections=[
                SectionDraft(
                    name=section["name"],
                    description=section["description"],
                    knowledge_points=[KnowledgePointDraft(
                        name=kp) for kp in section["knowledge_points"]]
                )
                for section in draft_data["sections"]
            ]
        )

        return {
            "messages": messages,
            "course_draft": course_draft,
            "draft_iteration": 1,
        }

    async def course_creator_node(self, state: State) -> Dict[str, Any]:
        """Create detailed course content from draft - one batch at a time"""
        if not state.get('course_draft'):
            raise ValueError("No course draft available for detailed creation")

        current_batch_index = state.get('current_batch_index', 0)
        total_batches = state.get('total_batches', 1)
        detailed_sections = state.get('detailed_sections', [])

        # Calculate which sections to process in this batch
        sections = state['course_draft'].sections
        start_idx = current_batch_index * self.max_sections_per_batch
        end_idx = min(start_idx + self.max_sections_per_batch, len(sections))
        batch = sections[start_idx:end_idx]

        log(
            f"Predefined Course Creator - Processing sections {start_idx + 1} to {end_idx} of {len(sections)} (batch {current_batch_index + 1} of {total_batches})")

        language = state['course_draft'].language

        system_prompt = """\
You are an expert course content writer. Based on the draft course structure, expand each knowledge point into detailed learning content.

For each **knowledge point**, provide:
- A clear, learner-friendly **description** of what the learner will gain
- A list of **relevant keywords** to support further exploration
- A **comprehensive explanation** that covers the core concept

**Course Context:**
Name: {name}
Description: {description}
Language: {language}

Focus:
- Ensure content supports **AI-powered wide learning**—broad, practical understanding over deep technical depth
- Keywords should help students effectively create prompts for AI tools
- Prioritize clarity and usefulness to give students the ability to effectively guide AI tools in this topic
- All content must be in {language}

Output Format:
Return a JSON object in the exact structure below:

{{
  "sections": [
    {{
      "name": "Section Name",
      "description": "What this section covers",
      "knowledge_points": [
        {{
          "name": "Knowledge Point Name",
          "description": "What the student will learn",
          "keywords": ["keyword1", "keyword2", ...],
          "content": "Detailed explanation of the concept"
        }}
      ]
    }}
  ]
}}
"""

        system_message = SystemMessage(content=system_prompt.format(
            name=state['course_draft'].name,
            description=state['course_draft'].description,
            language=language
        ))

        detail_prompt = """\
Now, please create detailed content for the following sections of the course:

{sections}
"""
        sections_data = []
        for section in batch:
            sections_data.append({
                "name": section.name,
                "description": section.description,
                "knowledge_points": [kp.name for kp in section.knowledge_points]
            })

        human_message = HumanMessage(content=detail_prompt.format(
            sections=json.dumps(sections_data, indent=2)
        ))

        current_messages = [system_message, human_message]

        response = await self.llm.ainvoke(current_messages, config={
            "configurable": {
                "model_kwargs": {"response_format": {"type": "json_object"}}
            }
        })

        # Strip whitespace and newlines from response content before parsing
        content = response.content.strip()
        content = repair_json(content)  # Repair any JSON formatting issues
        batch_data = json.loads(content)
        for section_data in batch_data["sections"]:
            detailed_section = Section(
                name=section_data["name"],
                description=section_data["description"],
                knowledge_points=[
                    KnowledgePoint(
                        name=kp["name"],
                        description=kp["description"],
                        keywords=kp["keywords"],
                        content=kp["content"]
                    )
                    for kp in section_data["knowledge_points"]
                ]
            )
            detailed_sections.append(detailed_section)

        # Update batch index
        next_batch_index = current_batch_index + 1

        # If this was the last batch, create the final CourseDetails
        if next_batch_index >= total_batches:
            course_details = CourseDetails(
                name=state['course_draft'].name,
                description=state['course_draft'].description,
                subheading=state['course_draft'].subheading,
                sections=detailed_sections,
                language=state['course_draft'].language,
                assignment_requirement=state['course_draft'].assignment_requirement,
                video_requirement=state['course_draft'].video_requirement,
                subject=state['course_draft'].subject
            )

            return {
                "course_details": course_details,
                "current_batch_index": next_batch_index,
                "detailed_sections": detailed_sections,
            }
        else:
            return {
                "current_batch_index": next_batch_index,
                "detailed_sections": detailed_sections,
            }

    async def course_creator_init_node(self, state: State) -> Dict[str, Any]:
        """Initialize course creation batch processing"""
        if not state.get('course_draft'):
            raise ValueError("No course draft available for detailed creation")

        sections = state['course_draft'].sections
        total_batches = (
            len(sections) + self.max_sections_per_batch - 1) // self.max_sections_per_batch

        log(
            f"Predefined Course Creator - Initializing batch processing: {len(sections)} sections, {total_batches} batches")

        return {
            "current_batch_index": 0,
            "total_batches": total_batches,
            "detailed_sections": []
        }

    def route_course_creator(self, state: State) -> str:
        """Route decision after course creator batch processing"""
        current_batch_index = state.get('current_batch_index', 0)
        total_batches = state.get('total_batches', 1)

        # If we have more batches to process, continue to course creator
        if current_batch_index < total_batches:
            return "course_creator"

        # If course creation is complete, check if we need to generate thumbnail
        if state.get('thumbnail_url') is None:
            return "generate_thumbnail"

        # Otherwise, we're done
        return "end"

    async def thumbnail_generator_node(self, state: State) -> Dict[str, Any]:
        """Generate thumbnail for course if one doesn't exist"""
        if not state.get('course_details'):
            raise ValueError(
                "No course details available for thumbnail generation")

        course_details = state['course_details']

        # Create image prompt based on course content
        from langchain_core.messages import SystemMessage
        prompt_system_message = SystemMessage(content=f"""
You are an AI image prompt specialist. Create a compelling, specific image prompt for a course thumbnail based on the course information provided.

The thumbnail should be:
- Professional and educational
- Visually appealing and engaging
- Clearly related to the course subject
- Suitable for a learning platform

Course Name: {course_details.name}
Course Description: {course_details.description}

Create a detailed image prompt that would generate an appropriate thumbnail image. Focus on visual elements that represent the course topic clearly. Be specific about style, composition, and visual elements.

Respond with just the image prompt, no additional text.
""")

        messages = [prompt_system_message]
        response = await self.llm.ainvoke(messages)

        image_prompt = response.content.strip()

        log(f"Generated image prompt for thumbnail: {image_prompt}")

        try:
            thumbnail_image_path = await generate_image_from_prompt(
                image_prompt,
                style='square',
            )
            if not thumbnail_image_path:
                log("Failed to generate thumbnail image, proceeding without thumbnail")
                return {"thumbnail_url": None}

            # Keep local file path as thumbnail URL in local-only mode
            thumbnail_url = thumbnail_image_path
            log(f"Generated thumbnail: {thumbnail_url}")
            return {"thumbnail_url": thumbnail_url}

        except Exception as e:
            log(f"Error generating thumbnail: {e}")
            # Return None if thumbnail generation fails - course can proceed without it
            return {"thumbnail_url": None}

    async def start_workflow(self, request_message: str, language: str = "English", thread_id: Optional[str] = None, thumbnail_url: Optional[str] = None):
        """
        Start the predefined course planning workflow.

        Args:
            request_message: Course creation request message
            language: Target language for the course (default: "English")
            thread_id: Optional thread identifier for this workflow session
            thumbnail_url: Optional URL for course thumbnail. If None, will generate one.

        Returns:
            course_data: Dictionary containing the complete course structure
        """
        try:
            if not thread_id:
                import uuid
                thread_id = f"predefined_course_{uuid.uuid4().hex}"

            # Initialize workflow state
            initial_state = {
                "messages": [HumanMessage(content=request_message)],
                "thread_id": thread_id,
                "language": language,
                "draft_iteration": 0,
                "course_draft": None,
                "course_details": None,
                "structured_response": None,
                "current_batch_index": 0,
                "total_batches": 0,
                "detailed_sections": [],
                "thumbnail_url": thumbnail_url,
            }

            config = {"recursion_limit": self.recursion_limit,
                      "configurable": {"thread_id": thread_id}}

            log(
                f"Starting predefined course planning workflow for language: {language}")

            # Run the workflow without interrupts
            final_state = await self.graph.ainvoke(initial_state, config)

            # Extract course details from final state
            course_details = final_state.get('course_details')
            if course_details:
                course_data = asdict(course_details)

                # Add thumbnail_url to course_data if available
                thumbnail_url = final_state.get('thumbnail_url')
                if thumbnail_url:
                    course_data['thumbnail_url'] = thumbnail_url

                # Update course data with hash and version - this creates the course_uid
                update_node_version(course_data)
                
                log(
                    f"Predefined course planning completed successfully: {course_data['name']}")
                return course_data
            else:
                raise ValueError(
                    "Workflow completed without generating course details")

        except Exception as e:
            log(f"Error in predefined course workflow: {e}")
            log(traceback.format_exc())
            raise e


class CoursePlannerWorkflow:
    """Compatibility wrapper used by webui routes."""

    def __init__(self) -> None:
        self._planner = PredefinedCoursePlannerWorkflow()

    def create_course_plan(self, requirement: str, language: str = "English") -> Dict[str, Any]:
        return asyncio.run(
            self._planner.start_workflow(
                request_message=requirement,
                language=language,
            )
        )


# Factory function for easy initialization
def create_predefined_course_planner() -> PredefinedCoursePlannerWorkflow:
    """Create and return a configured predefined course planner workflow"""
    return PredefinedCoursePlannerWorkflow()


async def main():
    """
    Main function to sync predefined courses from CMS.
    Checks for predefined_course_variant records with version -1 and creates course data.
    """

    cms = CMS()

    try:
        log("Starting predefined course sync...")

        # Get all predefined_course_variant records with version -1 (including drafts)
        variants = await cms.get_collection_records_by_filters('predefined-course-variant',
                                                              filters={'version': {'$eq': -1}},
                                                              include_drafts=True)

        if not variants:
            log("No predefined course variants with version -1 found.")
            return

        log(f"Found {len(variants)} predefined course variants to process.")

        # Create predefined course planner
        async with create_predefined_course_planner() as planner:

            for variant_record in variants:
                try:
                    variant = flatten_strapi_object(variant_record)
                    subtitle = variant.get('subtitle', 'Unknown')
                    prompt = variant.get('prompt', '')
                    language = variant.get('language', 'English')
                    # Get existing thumbnail_url
                    thumbnail_url = variant.get('thumbnail_url')

                    log(f"Processing course variant: {subtitle} in {language}")

                    # Create course data using the planner workflow
                    course_data = await planner.start_workflow(
                        request_message=prompt,
                        language=language,
                        thumbnail_url=thumbnail_url
                    )

                    if not course_data:
                        log(f"Failed to create course data for {subtitle}")
                        continue

                    # Update course data with hash and version using update_node_version
                    update_node_version(course_data)

                    # Extract fields for database update
                    assignment_requirement = course_data.get(
                        'assignment_requirement', 'General')
                    video_requirement = course_data.get(
                        'video_requirement', 'General')
                    sections = course_data.get('sections', [])
                    title = course_data.get('name', '')
                    description = course_data.get('description', '')
                    # Map subheading to subtitle
                    subtitle = course_data.get('subheading', '')
                    subject = course_data.get('subject', 'Learning')
                    uid = course_data.get('uid')
                    hash_value = course_data.get('hash')
                    version = course_data.get('version', 0)
                    generated_thumbnail_url = course_data.get(
                        'thumbnail_url')  # Get generated thumbnail_url

                    # Update the predefined_course_variant record
                    update_data = {
                        # Note: field name has typo in schema
                        'assignment_requirement': assignment_requirement,
                        'video_requirement': video_requirement,
                        'sections': sections,
                        'title': title,
                        'description': description,
                        'subtitle': subtitle,  # Map subheading to subtitle field in CMS
                        'subject': subject,
                        'course_uid': uid,
                        'hash': hash_value,
                        'version': version
                    }

                    # Only update thumbnail_url if one was generated (don't overwrite existing with None)
                    if generated_thumbnail_url:
                        update_data['thumbnail_url'] = generated_thumbnail_url

                    # Check if the related topic needs thumbnail_url update (use any available thumbnail)
                    available_thumbnail = generated_thumbnail_url or thumbnail_url
                    if available_thumbnail:
                        topic_relation = variant_record.get(
                            'attributes', {}).get('topic', {}).get('data')
                        if topic_relation:
                            topic_id = topic_relation.get('id')
                            if topic_id:
                                # Get the topic record to check if it has a thumbnail_url
                                topic_record = await cms.get_collection_record_by_id('predefined-course-topic', topic_id, include_drafts=True)
                                if topic_record:
                                    topic_data = flatten_strapi_object(
                                        topic_record)
                                    # If topic doesn't have thumbnail_url, use the available thumbnail
                                    if not topic_data.get('thumbnail_url'):
                                        await cms.update_collection_record('predefined-course-topic',
                                                                           topic_id,
                                                                           {'thumbnail_url': available_thumbnail})
                                        log(
                                            f"Updated topic thumbnail_url: {topic_data.get('course_topic', 'unknown')}")

                    await cms.update_collection_record('predefined-course-variant',
                                                       variant_record['id'],
                                                       update_data)

                    log(f"Successfully updated course variant: {subtitle}")

                except Exception as e:
                    log(
                        f"Error processing course variant {variant.get('subtitle', 'unknown')}: {str(e)}")
                    import traceback
                    log(traceback.format_exc())
                    continue

        log("Predefined course sync completed.")

    except Exception as e:
        log(f"Error in predefined course sync: {str(e)}")
        import traceback
        log(traceback.format_exc())
        raise
