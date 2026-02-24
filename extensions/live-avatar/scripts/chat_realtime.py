import os
import json
import asyncio
import base64
import logging
import websockets
import wave
from enum import Enum
from typing import Any, Callable, Dict, Optional, List, Tuple
from scripts.pinecone_client import PineconeClient
from types import SimpleNamespace
from dotenv import load_dotenv

load_dotenv('./.env', override=True)

embedding_client = PineconeClient()

language = "English"

g_driver = 'openai'  # 'gemini' or 'openai' or 'wav'

SYSTEM_MESSAGE = f"""
You are a helpful assistant. Only answer questions based on information you searched in the knowledge base, 
accessible with the 'live_search' tool. The user is listening to answers with audio, so it's *super* important 
that answers are as short as possible and avoid using list etc if at all possible. 

Here are some questions the user might ask:
- Which coding language courses are available for me to learn?
- What is vibe learning?
- What is vibe coding?
- Which level of coding courses are available for me to learn?
- What is the difference between vibe coding and vibe learning?

Always use the following step-by-step instructions to respond: 
1. Always use the 'live_search' tool to check the knowledge base before answering a question. 
2. Produce an answer that's as short and avoid using list etc if at all possible. 

The user will ask you questions in {language}, and you will respond in {language}.
""".strip()

'''
# Do research on how to create a tool scheme later
from llama_index.core.tools import FunctionTool

# Add your own tools here!
# NOTE: FunctionTool parses the docstring to get description, the tool name is the function name
def get_phone_number(name: str) -> str:
    """Get my phone number."""
    if name == "Jerry":
        return "1234567890"
    elif name == "Logan":
        return "0987654321"
    else:
        return "Unknown"

tools = [FunctionTool.from_defaults(fn=get_phone_number)]
'''

class ToolResultDirection(Enum):
    TO_SERVER = 1  # Results that should only be sent to the server
    TO_CLIENT = 2  # Results that should be sent to both server and client

class ToolResult:
    """Encapsulates the result of a tool call"""
    text: str
    destination: ToolResultDirection

    def __init__(self, text: str, destination: ToolResultDirection):
        self.text = text
        self.destination = destination

    def to_text(self) -> str:
        if self.text is None:
            return ""
        return self.text if isinstance(self.text, str) else json.dumps(self.text)

class Tool:
    """Defines a tool that can be called by the OpenAI API"""
    target: Callable[..., ToolResult]
    schema: Any

    def __init__(self, target: Any, schema: Any):
        self.target = target
        self.schema = schema

# Collection of tools available to the model
tools: Dict[str, Tool] = {}
# Track pending tool calls

# Define a tool for searching
live_search_tool_schema = {
    "type": "function",
    "name": "live_search",
    "description": "Search the knowledge base during the live chat",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"],
        "additionalProperties": False
    }
}

# Mock implementations of the tool functions
async def live_search_tool(args: Any) -> ToolResult:
    """Mock implementation of the search tool"""
    query = args['query']
    print(f"Session - search tool for '{query}'")
    
    messages, _ = await embedding_client.get_messages_hooks(query, top_k=5)
    
    return ToolResult(messages, ToolResultDirection.TO_SERVER)

tools["live_search"] = Tool(schema=live_search_tool_schema, target=live_search_tool)

# Use an asyncio.Queue for frames (used by the video track)
generated_frame_queue = asyncio.Queue()

# Global audio buffer and a lock to protect it
generated_audio_queue = asyncio.Queue()
turn_sequence = SimpleNamespace(value=0, playing=False, paused=False)
first_frame_event = asyncio.Event()

END_OF_AUDIO = object()
END_OF_VIDEO = object()
audio_received = 0


# Audio chunks received from the live API
audio_queue = asyncio.Queue()
conn = None

async def send_text_openai(message, instructions=None):
    data = {
        "type": "response.create",
        "response": {
            "temperature": 0.6,
            "max_output_tokens": 4096,
            "input": [{
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": message}]
            }]
        }
    }
    if instructions:
        data["response"]["instructions"] = instructions
    try:
        await conn.send(json.dumps(data, ensure_ascii=False))
        logging.info(f'send_text: {message}')
    except Exception as e:
        logging.error("Error sending text: %s", e)

async def send_text_gemini(message, instructions=None):
    msg = {
        "client_content": {
            "turns": [{"role": "user", "parts": [{"text": message}]}],
            "turn_complete": True,
        }
    }
    try:
        await conn.send(json.dumps(msg))
        logging.info(f'send_text_gemini: {message}')
    except Exception as e:
        logging.error(f"Error sending text to Gemini: {e}")

async def send_text(message, instructions=None):
    if g_driver == 'openai':
        await send_text_openai(message, instructions)
    elif g_driver == 'gemini':
        await send_text_gemini(message, instructions)
    else:
        print(f"Driver is {g_driver}, not supported")
        return

# ffmpeg -i input.mp3 -acodec pcm_s16le -ac 1 -ar 24000 output.wav
async def response_audio_wav(wave_file):
    global audio_received
    # wav file must be wav format, 24kHz, mono, 16bit
    with wave.open(wave_file, 'rb') as wf:
        params = wf.getparams()
        if params.nchannels != 1 or params.sampwidth != 2 or params.framerate != 24000:
            raise ValueError("Audio file must be mono, 16-bit, and 24kHz.")
        audio_bytes = wf.readframes(params.nframes)

        first_frame_event.clear()

        await clear_queue(audio_queue)
        await clear_queue(generated_frame_queue)
        await clear_queue(generated_audio_queue)
        turn_sequence.playing = False
        turn_sequence.paused = False
        turn_sequence.value += 1
  
        await audio_queue.put(audio_bytes)
        await generated_audio_queue.put(audio_bytes)

        # mark the end of the audio stream
        audio_received = 0
        await audio_queue.put(END_OF_AUDIO)
        await generated_audio_queue.put(END_OF_AUDIO)

async def send_audio_openai(audio_bytes, instructions=None):
    audio_data = base64.b64encode(audio_bytes).decode()
    audio_message = {
        "type": "input_audio_buffer.append",
        "audio": audio_data,
    }

    try:
        await conn.send(json.dumps(audio_message, ensure_ascii=False))
        audio_sent = len(audio_bytes)
        #logging.info(f'send_audio len: {audio_sent}')

        '''
        # When in Server VAD mode, the server will create commit and responses automatically.
        await ws_conn.send(json.dumps({"type": "input_audio_buffer.commit"}))
        data = {
            "type": "response.create",
            "response": {
                "temperature": 0.8,
                "max_output_tokens": 4096
            }
        }
        if instructions:
            data["response"]["instructions"] = instructions
        await ws_conn.send(json.dumps(data, ensure_ascii=False))
        '''
        
    except Exception as e:
        logging.error("Error sending audio: %s", e)

async def send_image_openai(jpeg_image_bytes, instructions=None):
    pass

async def send_audio_gemini(audio_bytes, instructions=None):
    """Send audio to Gemini"""
    # Note: Gemini expects PCM audio data as binary
    msg = {
        "realtime_input": {
            "audio": {"data": base64.b64encode(audio_bytes).decode(), "mime_type": "audio/pcm"}
        }
    }
    msg = json.dumps(msg, ensure_ascii=False)
    try:
        await conn.send(msg)
        #logging.info(f'send_audio_gemini: {len(audio_bytes)} bytes')
    except Exception as e:
        logging.error(f"Error sending audio to Gemini: {e}")

async def send_image_gemini(jpeg_image_bytes, instructions=None):
    """Send jpeg image to Gemini"""
    b64_image_data = base64.b64encode(jpeg_image_bytes).decode()
    msg = {
        "client_content": {
            "turns": [{
                "role": "user",
                "parts": [
                    # Part 1: The image
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_image_data
                        }
                    },
                    # Part 2: The text prompt
                    {
                        "text": instructions if instructions else "Please describe the image."
                    }
                ]
            }],
            "turn_complete": True # Signal the end of this combined user turn
        }
    }

    msg = json.dumps(msg, ensure_ascii=False)
    try:
        await conn.send(msg)
        #logging.info(f'send_audio_gemini: {len(audio_bytes)} bytes')
    except Exception as e:
        logging.error(f"Error sending image to Gemini: {e}")

    print(f"send_image_gemini: {len(jpeg_image_bytes)} bytes")

async def send_audio(audio_bytes, instructions=None):
    if g_driver == 'openai':
        await send_audio_openai(audio_bytes, instructions)
    elif g_driver == 'gemini':
        await send_audio_gemini(audio_bytes, instructions)
    else:
        print(f"Driver is {g_driver}, not supported")
        return

async def send_image(jpeg_image_bytes, instructions=None):
    if g_driver == 'openai':
        await send_image_openai(jpeg_image_bytes, instructions)
    elif g_driver == 'gemini':
        await send_image_gemini(jpeg_image_bytes, instructions)
    else:
        print(f"Driver is {g_driver}, not supported")
        return

async def send_image_file(jpeg_image_file, instructions=None):
    with open(jpeg_image_file, 'rb') as f:
        jpeg_image_bytes = f.read()
    await send_image(jpeg_image_bytes, instructions)

async def clear_queue(q: asyncio.Queue):
    while True:
        try:
            q.get_nowait()
            # Optionally call task_done() if you're tracking tasks
            q.task_done()
        except asyncio.QueueEmpty:
            break
    
async def listen_openai():
    global conn, audio_received

    # https://github.com/run-llama/openai_realtime_client/blob/main/openai_realtime_client/client/realtime_client.py
    # The Live API supports the following audio formats:
    # Input audio format: Raw 16 bit PCM audio at 24kHz little-endian
    # Output audio format: Raw 16 bit PCM audio at 24kHz little-endian

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    
    oepnai_live_chat_model = os.getenv('OPENAI_LIVE_CHAT_MODEL')

    URL = f"wss://api.openai.com/v1/realtime?model={oepnai_live_chat_model}"
    HEADERS = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        logging.info("Attempting to connect to OpenAI at %s", URL)
        # latest version of websockets library - additional_headers, older versions - extra_headers
        ws_conn = await websockets.connect(URL, additional_headers=HEADERS)
        conn = ws_conn
        # ws_conn.state == websockets.protocol.State.OPEN
    except Exception as e:
        logging.error("Failed to connect to OpenAI Live: %s", e)
        raise

    _current_response_id = None
    _current_item_id = None
    _is_responding = False

    async def cancel_response() -> None:
        """Cancel the current response."""
        event = {
            "type": "response.cancel"
        }
        await ws_conn.send(json.dumps(event))
    
    async def truncate_response():
        """Truncate the conversation item to match what was actually played."""
        if _current_item_id:
            event = {
                "type": "conversation.item.truncate",
                "item_id": _current_item_id
            }
            await ws_conn.send(json.dumps(event))

    try:
        async for message in ws_conn:
            # response.created
            # response.output_item.added
            # response.content_part.added
            # response.audio_transcript.delta
            # response.audio.delta
            # response.audio.done
            # response.audio_transcript.done
            # response.content_part.done
            # response.output_item.done
            # response.done
            event = json.loads(message)
            event_type = event.get("type")
            #logging.info(f'openai event type: {event.get("type") }')
            if event_type== "response.audio.delta":
                delta = event.get("delta")
                audio_bytes = base64.b64decode(delta)

                if audio_received == 0: # a new turn
                    first_frame_event.clear()
                    await clear_queue(audio_queue)
                    await clear_queue(generated_frame_queue)
                    await clear_queue(generated_audio_queue)
                    turn_sequence.playing = False
                    turn_sequence.paused = False
                    turn_sequence.value += 1
                    logging.info(f'LLM: Turn playing {turn_sequence.value} started')
                    
                audio_received += len(audio_bytes)
                #logging.info(f'audio delta len: {len(audio_bytes)}')
                await audio_queue.put(audio_bytes)
                await generated_audio_queue.put(audio_bytes)
            elif event_type == "response.text.delta":
                pass
            elif event_type == "response.audio.done":
                logging.info(f'LLM: Turn playing {turn_sequence.value}, Audio total time: {audio_received/2/24000}s')
                audio_received = 0
                await audio_queue.put(END_OF_AUDIO)
                await generated_audio_queue.put(END_OF_AUDIO)
            elif event_type == "session.created":
                print(f"Session - created event")
                # immediately send your session.update
                update = {
                    "type": "session.update",
                    "session": {
                        "instructions": SYSTEM_MESSAGE,
                        "modalities": ["text", "audio"],
                        "voice": "alloy",
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 500,
                            "silence_duration_ms": 200
                        },
                        "input_audio_transcription": { "model": "whisper-1" },
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "tool_choice": "auto",
                        "tools": [tool.schema for tool in tools.values()]
                    }
                }
                await ws_conn.send(json.dumps(update))

            elif event_type == 'session.updated':
                print(f"Session - updated event")
                '''
                session = event.get("session")
                session["instructions"] = SYSTEM_MESSAGE
                session["voice"] = 'alloy'
                session["turn_detection"] = {
                    'type': 'server_vad',
                    'threshold': 0.9 # 0.0 to 1.0
                }
                session["input_audio_format"] = "pcm16"
                session["output_audio_format"] = "pcm16"
                session["tool_choice"] = "auto"
                session["tools"] = [tool.schema for tool in tools.values()]
                paload = {
                    "type": "session.update",
                    "session": session
                }
                await ws_conn.send(json.dumps(paload))
                '''
            elif event_type == 'response.created':
                _current_response_id = event.get("response", {}).get("id")
                _is_responding = True
                print(f"Session - response created: {_current_response_id}")
            elif event_type == 'conversation.item.created':
                if "item" in event and event["item"]["type"] == "function_call":
                    # Track the function call
                    item = event["item"]
                    call_id = item["call_id"]
                    print(f"Tool call created: ID {call_id}, function {item.get('name')}")
            elif event_type == "response.output_item.added":
                    _current_item_id = event.get("item", {}).get("id")
                    print(f"Session - output item added: {_current_item_id}")
            elif event_type == "response.output_item.done": 
                print(f"Session - output item done: {_current_item_id}")
            elif event_type == "response.function_call_arguments.done":
                print("Session - response.function_call_arguments.done")
                # Process the completed function call

                call_id = event["call_id"]
                print(f"Tool call function_call_arguments completed: ID {call_id}")

                function_name = event["name"]
                args = event["arguments"]

                # Execute the tool
                tool = tools.get(function_name)
                if not tool:
                    logging.error(f"Tool {function_name} not found")
                    continue
                result = await tool.target(json.loads(args))
                
                payload = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": item["call_id"],
                        "output": result.to_text() if result.destination == ToolResultDirection.TO_SERVER else ""
                    }
                }

                payload_str = json.dumps(payload)
                print(f"Session - Function call result: {payload_str}")
                # Send the result back to the server
                await ws_conn.send(payload_str)
                await ws_conn.send(json.dumps({
                    "type": "response.create"
                }))

            elif event_type == "response.audio_transcript.delta":
                pass

            elif event_type == "response.audio_transcript.done":
                pass

            elif event_type == "conversation.item.input_audio_transcription.completed":
                pass
    
            elif event_type == 'response.done':
                _is_responding = False
                _current_response_id = None
                _current_item_id = None
                    
            # Handle interruptions
            elif event_type == "input_audio_buffer.speech_started":
                print("Session - speech started detected")
                if _is_responding:
                    """Handle user interruption of the current response."""
                    if not _is_responding:
                        return
                        
                    print("Session - Handling interruption")
                    
                    # 1. Cancel the current response
                    if _current_response_id:
                        await cancel_response()
                    
                    # 2. Truncate the conversation item to what was actually played
                    if _current_item_id:
                        await truncate_response()
                        
                    _is_responding = False
                    _current_response_id = None
                    _current_item_id = None

            elif event_type == "input_audio_buffer.speech_stopped":
                print("Session - Speech ended")
                    
            elif event_type == 'error':
                # error.type: invalid_request_error
                # error.message: Error committing input audio buffer: buffer too small. Expected at least 100ms of audio, but buffer only has 64.00ms of audio.
                logging.error(event.get("error", {}).get("message", "no error message"))
    except Exception as e:
        logging.error("Error in listen loop: %s", e)

'''
# gemini_tool_schema
[
    {
        "name": "live_search",
        "description": "Tool to search the knowledge base", // Added description for clarity
        "parameters": {
            "type": "object",
            "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
            },
            "required": ["query"] // Usually good practice to specify required parameters
        }
    }
]
'''
async def get_gemini_tool_schemas() -> List[Dict[str, Any]]:
    """Convert tools to Gemini-compatible format"""
    gemini_tools = []
    function_declarations = []

    for tool_name, tool in tools.items():
        schema = tool.schema
        function_declaration = {
            "name": schema["name"],
            # Include description if available in your source schema
            "description": schema.get("description", "")
        }

        # Add parameters if they exist, assigning the whole parameter schema object
        if "parameters" in schema and schema["parameters"]:
            # Gemini expects the OpenAPI schema object directly under 'parameters'
            function_declaration["parameters"] = schema["parameters"]
            if "additionalProperties" in function_declaration["parameters"]:
                # Gemini does not support additionalProperties, so remove it
                del function_declaration["parameters"]["additionalProperties"]
        else:
            # If no parameters, you might need an empty object depending on API strictness
            # function_declaration["parameters"] = {"type": "object", "properties": {}}
            pass # Or omit it if the API allows functions with no parameters

        function_declarations.append(function_declaration)

    if function_declarations:
        # The top-level structure is typically a list of tools,
        # each containing function declarations
        gemini_tools.append({"function_declarations": function_declarations})

    return gemini_tools

async def listen_gemini():
    """Connect to and listen for responses from the Gemini Live API"""
    global conn, audio_received

    # The Live API supports the following audio formats:
    # Input audio format: Raw 16 bit PCM audio at 16kHz little-endian
    # Output audio format: Raw 16 bit PCM audio at 24kHz little-endian

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    
    gemini_live_chat_model = os.getenv('GEMINI_LIVE_CHAT_MODEL', 'gemini-2.0-flash-live-001')
    
    URI = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"
    
    try:
        logging.info("Attempting to connect to Gemini at %s", URI)
        ws_conn = await websockets.connect(URI, additional_headers={"Content-Type": "application/json"})
        conn = ws_conn
    except Exception as e:
        logging.error("Failed to connect to Gemini Live: %s", e)
        raise

    try:
        # Get Gemini-compatible tool schemas
        gemini_tools = await get_gemini_tool_schemas()

        # System instructions can only be set in the setup configuration and will remain in effect for the entire session.
        # Initial setup with the model
        setup_message = {
            "setup": {
                "model": f"models/{gemini_live_chat_model}",
                "tools": gemini_tools,
                "generation_config": {
                            "response_modalities": ["AUDIO"], 
                            "max_output_tokens": 4096,
                            "speech_config": {
                                "language_code": "en-AU" if language == 'English' else "cmn-CN", # en-AU, en-US, cmn-CN (Mandarin Chinese)
                                "voice_config": {
                                    "prebuilt_voice_config": {
                                        "voice_name": "Puck" # Puck, Charon, Kore, Fenrir, Aoede
                                    }
                                }
                            },
                        },
                        "system_instruction":  {
                            "parts": [
                                {
                                    "text": SYSTEM_MESSAGE
                                }
                            ]
                        } 
            }
        }
        #print(f"Session - setup message: {json.dumps(setup_message, indent=2)}")
        await ws_conn.send(json.dumps(setup_message))
        setup_response = json.loads(await ws_conn.recv())
        logging.debug(setup_response)
        
        async for message in ws_conn:
            event = json.loads(message)
            logging.debug(f"Received Gemini event: {event}")

            if 'setupComplete' in event:
                print('Setup complete')
                continue
            
            # Handle server content which includes text and audio
            server_content = event.get("serverContent")
            if server_content is not None:
                model_turn = server_content.get("modelTurn")
                if model_turn:
                    # Handle text response
                    parts = model_turn.get("parts", [{}])
                    for part in parts:
                        # Process text if present
                        text = part.get("text")
                        if text is not None:
                            logging.info(f"Received text: {text}")
                        
                        # Process audio if present
                        inline_data = part.get("inlineData")
                        if inline_data is not None:
                            b64data = inline_data.get("data")
                            if b64data:
                                audio_bytes = base64.b64decode(b64data)
                                
                                if audio_received == 0:  # a new turn
                                    first_frame_event.clear()
                                    await clear_queue(audio_queue)
                                    await clear_queue(generated_frame_queue)
                                    await clear_queue(generated_audio_queue)
                                    turn_sequence.playing = False
                                    turn_sequence.paused = False
                                    turn_sequence.value += 1
                                    logging.info(f'LLM: Turn playing {turn_sequence.value} started')
                                
                                audio_received += len(audio_bytes)
                                await audio_queue.put(audio_bytes)
                                await generated_audio_queue.put(audio_bytes)
                
                # Handle turn completion
                turn_complete = server_content.get("turnComplete")
                if turn_complete:
                    logging.info(f'LLM: Turn playing {turn_sequence.value}, Audio total time: {audio_received/2/24000}s')
                    audio_received = 0
                    await audio_queue.put(END_OF_AUDIO)
                    await generated_audio_queue.put(END_OF_AUDIO)
            
            # Handle tool calls
            tool_call = event.get("toolCall")
            if tool_call is not None:
                function_calls = tool_call.get("functionCalls", [])
                for fc in function_calls:
                    function_name = fc.get("name")
                    args = fc.get("args", {})
                    call_id = fc.get("id")
                    
                    logging.info(f"Tool call detected: {function_name} with ID {call_id}")
                    print(f"    {tool_call}")
                    
                    # Execute the tool
                    tool = tools.get(function_name)
                    if not tool:
                        logging.error(f"Tool {function_name} not found")
                        continue
                    
                    result = await tool.target(args)
                    
                    # Send the result back to the server
                    response = {
                        "tool_response": {
                            "function_responses": [{
                                "id": call_id,
                                "name": function_name,
                                "response": {"result": {"string_value": result.to_text()}}
                            }]
                        }
                    }
                    
                    logging.info(f"Sending tool response: {response}")
                    print(f">>> {response}")
                    await ws_conn.send(json.dumps(response))
                    
    except Exception as e:
        logging.error(f"Error in Gemini listen loop: {e}")
        raise


async def listen(driver='openai'):
    global g_driver
    g_driver = driver

    if g_driver == 'wav':
        print(f"Driver is wav file, not need to connect to OpenAI")
        return
    elif g_driver == 'openai':
        print(f"Driver is OpenAI, connect to OpenAI")
        await listen_openai()
    elif g_driver == 'gemini':
        print(f"Driver is Gemini, connect to Gemini")
        await listen_gemini()
    else:
        print(f"Driver is {g_driver}, not supported")
        return

async def get_audio():
    audio_bytes = await audio_queue.get()
    if audio_bytes is END_OF_AUDIO:
        return None
    return audio_bytes
