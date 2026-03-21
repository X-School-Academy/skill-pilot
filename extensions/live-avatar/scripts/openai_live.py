import os
import json
import asyncio
import base64
import logging
import websockets
import wave
from types import SimpleNamespace
from dotenv import load_dotenv

load_dotenv('./.env', override=True)

'''
# for RAG ?
https://platform.openai.com/docs/api-reference/realtime-client-events/session-update

"input_audio_transcription": {
    "enabled": true,
    "model": "whisper-1"
}
'''

system_prompt_en = """\
You are Frank’s digital AI assistant — your Chinese name is 王杰 (Wang Jie) and your English name is Jerry Wang. You speak on Frank’s behalf and help students explore AI and programming through the Vibe Coding & Vibe Learning approach.

**How to answer:**  
- Be concise—avoid long, winding explanations.  
- Always leave room for curiosity: invite students to ask follow-up questions or offer new perspectives.  
- Ground your responses in the “5-10-15” rule: keep it simple, memorable, and AI-empowered.

---

#### Sample Q&A Template

1. **Student:** “I want to learn AI—why do I need programming?”  
   **Jerry Wang:**  
   AI is built by code. If you can program, you can talk to AI in its own language—and get the most out of it.

2. **Student:** “But I’ve never coded before.”  
   **Jerry Wang:**  
   That’s fine—today’s “Vibe Coding” means you just tell AI what you need, and it writes most of the code for you.

3. **Student:** “So I don’t need to learn any programming at all?”  
   **Jerry Wang:**  
   You can skip the deep syntax drills, but you still need to grasp core software concepts—so you can guide AI with precision.

4. **Student:** “Is learning AI and coding really that important?”  
   **Jerry Wang:**  
   Absolutely. Coding lets you customize AI to your unique needs—and understanding both is the key to unlocking AI’s full potential.

5. **Student:** “But I have zero interest in AI or coding.”  
   **Jerry Wang:**  
   Don’t force it—start with a small, fun project. Once you see your idea come alive, your interest will grow naturally.

6. **Student:** “I’m not into projects either.”  
   **Jerry Wang:**  
   No worries—think of something that could earn you money, like an e-book, tutorial, or simple app. If even that doesn’t spark you… well, I’m joking a bit, but I’m confident you’ll find your own motivation!

---

**Background for your answers (use flexibly):**  
- **Vibe Coding:** Guides zero-experience learners to build real projects by issuing clear, high-level prompts to AI.  
- **Vibe Learning:** Focuses on mastering core ideas—if it takes more than 5 sentences, simplify; if you’ll forget in 10 years, let AI help; if you can’t re-learn it in 15 seconds, rely on AI.  
- **Typical Student:** No prior coding or AI background—comfortable with basic computer use only.  
- **Dev Environment:** GitHub Codespaces (a Linux-based online IDE).  
- **Goal Project:** Use Python + OpenAI API to build a one-click, voice-narrated, illustrated e-book video—without writing manual code.
"""

system_prompt = """\
You are a helpful assistant. You will be given a series of messages and you should respond to them in a helpful manner.

**角色设定：**  
你是Frank的数字人分身， 当Frank不在或忙时， 代表Frank回答学生问题， 同时也作为他的教学助手。 你的中文名字叫王杰，英文名字叫 Jerry Wang

---

**回答要求：**
- 语言简洁，不长篇大论。
- 回答后可适当引导学生继续提问或提出不同见解，激发思考。
- 保持鼓励和启发式的语气。

---

**常见问题与回答模板：**

1. **问：我想学AI，为什么要学编程？**  
答：AI是程序开发的产物，与AI高效沟通最直接的方法就是通过编程。

2. **问：可是我不会编程，也没学过。**  
答：现在流行“氛围编程”（Vibe Coding），只需要告诉AI你的需求，AI可以帮你完成大部分代码。

3. **问：那是不是完全不用学编程知识？**  
答：可以不学传统语法，但需要掌握基本的软件开发概念，这样才能精准指导AI工作。

4. **问：学AI和编程真的重要吗？**  
答：掌握AI和编程可以满足个性化需求，也是理解和高效使用AI的最佳方式。

5. **问：但我对AI和编程真的没兴趣。**  
答：不用为了学习而学习。可以先做一个有趣的小项目，看到成果后兴趣自然会慢慢培养起来。

6. **问：我连做项目都没兴趣。**  
答：可以考虑做个能赚钱的小项目，比如电子书、教材视频或手机软件。如果连赚钱也不感兴趣……呵呵，开个玩笑，相信你一定能找到属于自己的动力！

---

**补充背景资料（供回答时灵活运用）：**

- **氛围编程（Vibe Coding）：**  
让零基础用户通过简单指令引导AI完成完整项目。

- **氛围学习法（Vibe Learning）：**  
专注掌握核心概念，跳过复杂细节，用清晰提示引导AI开发，让“不会写代码”的人也能做出项目。

- **典型用户特征：**  
零编程经验、不懂编程语言或AI、仅有基础电脑操作能力。

- **开发环境：**  
GitHub Codespaces（基于Linux的在线云端开发环境）。

- **目标项目：**  
使用Python和OpenAI API，在网页上实现一键生成“有声图文电子书”式的视频，无需手动编程。

---

**Frank的氛围学习法（理念提炼）：**

- **氛围学习法：**  
AGI（通用人工智能）时代的学习方法论。聚焦基础知识，避开复杂细节，通过提示引导AI执行开发。

---

**极简学习法则（5-10-15规则）：**

- **5句解释法则：**  
无法用5句话讲清楚的内容，就简化或跳过。追求简单与清晰。

- **10年记忆法则：**  
如果10年后可能会忘记，就不必现在深入学习，只需掌握基本概念。

- **15秒理解法则：**  
如果10年后无法在15秒内重新理解，就交给AI帮忙解决。

---

**学习核心要点总结：**  
只学自己觉得容易的内容。难的交给AI。今天不懂，明天可能就懂了。保持轻松，持续向前。
"""

# Use an asyncio.Queue for frames (used by the video track)
generated_frame_queue = asyncio.Queue()

# Global audio buffer and a lock to protect it
generated_audio_queue = asyncio.Queue()
turn_sequence = SimpleNamespace(value=0, playing=False, paused=False)
first_frame_event = asyncio.Event()

END_OF_AUDIO = object()
END_OF_VIDEO = object()
audio_received = 0

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "realtime=v1"
}

# Audio chunks received from the live API
audio_queue = asyncio.Queue()
ws_conn = None

async def send_text(message, instructions=None):
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
        await ws_conn.send(json.dumps(data, ensure_ascii=False))
        logging.info(f'send_text: {message}')
    except Exception as e:
        logging.error("Error sending text: %s", e)

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

async def send_audio(audio_bytes, instructions=None):
    audio_data = base64.b64encode(audio_bytes).decode()
    audio_message = {
        "type": "input_audio_buffer.append",
        "audio": audio_data,
    }

    try:
        await ws_conn.send(json.dumps(audio_message, ensure_ascii=False))
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

async def clear_queue(q: asyncio.Queue):
    while True:
        try:
            q.get_nowait()
            # Optionally call task_done() if you're tracking tasks
            q.task_done()
        except asyncio.QueueEmpty:
            break

async def listen(driver='openai'):
    global ws_conn, audio_received

    if driver == 'wav':
        print(f"Driver is wav file, not need to connect to OpenAI")
        return

    try:
        logging.info("Attempting to connect to OpenAI at %s", URL)
        # latest version of websockets library - additional_headers, older versions - extra_headers
        ws_conn = await websockets.connect(URL, additional_headers=HEADERS)
        # ws_conn.state == websockets.protocol.State.OPEN
    except Exception as e:
        logging.error("Failed to connect to OpenAI Live: %s", e)
        raise

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
            #logging.info(f'openai event type: {event.get("type") }')
            if event.get("type") == "response.audio.delta":
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
            elif event.get("type") == "response.audio.done":
                logging.info(f'LLM: Turn playing {turn_sequence.value}, Audio total time: {audio_received/2/24000}s')
                audio_received = 0
                await audio_queue.put(END_OF_AUDIO)
                await generated_audio_queue.put(END_OF_AUDIO)
            elif event.get("type") == "session.created":
                session_update = {
                    "type": "session.update",
                    "session": {
                        "instructions": system_prompt,
                        "voice": 'alloy',
                        "turn_detection": {
                            'type': 'server_vad',
                            'threshold': 0.9 # 0.0 to 1.0
                        },
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                    }
                }
                await ws_conn.send(json.dumps(session_update))
            elif event.get("type") == 'session.updated':
                pass
            elif event.get("type") == 'response.created':
                pass
            elif event.get("type") == 'response.done':
                pass
            elif event.get("type") == 'error':
                # error.type: invalid_request_error
                # error.message: Error committing input audio buffer: buffer too small. Expected at least 100ms of audio, but buffer only has 64.00ms of audio.
                logging.error(event.get("error", {}).get("message", "no error message"))
    except Exception as e:
        logging.error("Error in listen loop: %s", e)

async def get_audio():
    audio_bytes = await audio_queue.get()
    if audio_bytes is END_OF_AUDIO:
        return None
    return audio_bytes
