#!/usr/bin/env python
import sys
import logging

def setup_logging(log_file="/var/log/live_chat.log"):
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stderr),  # Send logs to stderr
            logging.FileHandler(log_file, mode='a')
        ]
    )
# init before other import
setup_logging()

import time
import argparse
import asyncio
import json
import os
import numpy as np
from aiohttp import web
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    VideoStreamTrack,
    AudioStreamTrack,
    RTCConfiguration,
    RTCIceServer
)
from aiortc.contrib.media import MediaPlayer, MediaRecorder, MediaBlackhole
from av import VideoFrame, AudioFrame
from av.audio.resampler import AudioResampler
from fractions import Fraction
from scripts.openai_live import response_audio_wav, send_text as llm_live_send_text, send_audio as llm_live_send_audio, listen as llm_live_listen , first_frame_event, generated_audio_queue, END_OF_AUDIO, END_OF_VIDEO, generated_frame_queue, turn_sequence, clear_queue
from scripts.live_inference import init_live_inference, start_live_inference
import glob
import cv2
import torch
from dotenv import load_dotenv

load_dotenv('./.env', override=True)

# pip install silero-vad
# or using torch.hub
vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
(get_speech_ts, _, _, _, _) = utils

VIDEO_CLOCK_RATE = 90000
VIDEO_TIME_BASE = Fraction(1, VIDEO_CLOCK_RATE)

video_fps = 25

pcs = set()
ws_client = None  # Global websocket connection (for this prototype only)
current_pc = None  # Global reference to the active peer connection
mic_muted = True  # Global flag to indicate whether the mic is muted
avatar = ''
driver = 'openai'

predefined_message_instructions = """\
Repeat the text exactly as provided, applying the specified emotional or voice style if asked.
Do not add any introductory phrases, explanations, or commentary in the audio output.
Speak only the text given, in the required tone."""

if os.environ.get("TURN_SERVER_URLS") is None:
    print("ENV TURN_SERVER_URLS is not set")

async def index(request):
    try:
        with open(os.path.join(os.path.dirname(__file__), "live_chat.html"), "r") as f:
            content = f.read()
            content = content.replace('{{TURN_SERVER_URLS}}', os.environ.get("TURN_SERVER_URLS"))
            content = content.replace('{{TURN_SERVER_USERNAME}}', os.environ.get("TURN_SERVER_USERNAME"))
            content = content.replace('{{TURN_SERVER_PASSWORD}}', os.environ.get("TURN_SERVER_PASSWORD"))
    except Exception as e:
        return web.Response(status=500, text=str(e))
    return web.Response(content_type="text/html", text=content)

class VideoTrack(VideoStreamTrack):
    """
    Custom video track that pulls frames from an asyncio queue.
    """
    def __init__(self, fps=25):
        super().__init__()
        self.fps = fps
        self.welcome_sent = False
        self.current_turn_sequence = -1
        self.start_time = None
        self.played_time = 0
        self.silent_index = 0
        self.silent_images = []
        self.video_started = False
        self.turn_start = 0
        self.turn_duration = 0
        self.turn_frames = 0

        #ffmpeg -i ryan-slient-25fps-500ms.mp4 frame_%03d.png
        png_files = sorted(glob.glob(f"data/silent/{avatar}/frame_*.png"))
        if not png_files:
            raise FileNotFoundError("No png images found. Ensure ffmpeg extracted frames to png format.")

        for file in png_files:
            img = cv2.imread(file)
            if img is not None:
                self.silent_images.append(img)
            else:
                logging.error(f"Failed to load image {file}")

        # Total number of images (max)
        n = len(self.silent_images)

        # Build the silent playback sequence.
        # Pattern: 1,2,3,...,n, (n-1), ..., 2,1,2 (in 1-indexed terms)
        # Convert to 0-indexed: ascending: 0,1,2,...,n-1; descending: n-2,...,1,0; then extra index 1.
        ascending = list(range(n))
        descending = list(range(n - 2, -1, -1)) if n >= 2 else []
        self.silent_sequence = ascending + descending + ([1] if n > 1 else [0])

        # If self.fps is less than 25, skip some frames from the sequence.
        if self.fps < 25:
            skip_factor = int(round(25 / self.fps))
            self.silent_sequence = self.silent_sequence[::skip_factor]
            # Ensure sequence is not empty.
            if not self.silent_sequence:
                self.silent_sequence = [0]

    def getNextSilentFrame(self):
        index = self.silent_sequence[self.silent_index]
        frame = self.silent_images[index]
        self.silent_index = (self.silent_index + 1) % len(self.silent_sequence)
        return frame, 1/self.fps

    async def recv(self):
        if not self.welcome_sent:
            await llm_live_send_text("Please ask the user 'What I can help you today?'")
            #await llm_live_send_text("Please ask the user 'What I can help you today?' in Chinese")
            self.welcome_sent = True

        #await first_frame_event.wait()  # wait until first frame is ready
        while True:
            try:
                frameInfo = generated_frame_queue.get_nowait()
                frame = frameInfo.frame
                duration = frameInfo.duration
                if frame is END_OF_VIDEO or turn_sequence.paused:
                    frame, duration = self.getNextSilentFrame()
                    #logging.warning(f"Video is ended, played time {time.monotonic() - self.turn_start} : duration {self.turn_duration} : frames {self.turn_frames} ...........")
                    self.video_started = False
                else:
                    if not self.video_started:
                        self.video_started = True
                        self.turn_start = time.monotonic()
                        self.turn_duration = duration
                        self.turn_frames  = 1
                        logging.warning(f"Video is started at {self.played_time} ...........")
                    else:
                        self.turn_duration += duration
                        self.turn_frames += 1
            except asyncio.QueueEmpty:
                if self.video_started:
                    await asyncio.sleep(0.002)
                    continue
                else:
                    frame, duration = self.getNextSilentFrame()
            break

        now = time.monotonic()
        # Initialize start time once (anchoring to a hardware clock)
        if self.start_time is None:
            self.start_time = now

        # Calculate the scheduled time for the next frame.
        scheduled_time = self.start_time + self.played_time + duration
        delay = scheduled_time - now

        if delay > 0:
            await asyncio.sleep(delay)
            target_time = scheduled_time
            self.played_time += duration
        else:
            logging.warning("Frame processing is lagging by %.3f seconds", -delay)
            # Update the target time and re-sync played_time.
            target_time = time.monotonic()
            self.played_time = target_time - self.start_time

        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = int(target_time * VIDEO_CLOCK_RATE)
        video_frame.time_base = VIDEO_TIME_BASE

        return video_frame

class AudioTrack(AudioStreamTrack):
    """
    Custom audio track that streams fixed-duration audio chunks in real time,
    resetting its timing after long gaps.
    """
    def __init__(self, sample_rate=24000):
        super().__init__()
        self.sample_rate = sample_rate
        self.num_samples = 960 // 2  # 24000 / 960 = 25 frames per second, 480 - 0.02 sec
        self.chunk_size = self.num_samples * 2  # assuming 16-bit samples
        self._frame_index = 0    # counter for frames in the current sentence
        self._start_time = None  # reference start time for the current sentence
        self._buffer = bytearray()
        self.current_turn_sequence = -1
        self.audio_started = False
        self.turn_start = 0
        self.turn_duration = 0

    async def recv(self):

        while len(self._buffer) < self.chunk_size:
            missing = self.chunk_size - len(self._buffer)
            if turn_sequence.playing and not turn_sequence.paused:
                try:
                    data = generated_audio_queue.get_nowait()
                    if data is END_OF_AUDIO:
                        self._buffer.extend(b'\0' * missing)
                        logging.warning(f"Audio is ended, played time {time.monotonic() - self.turn_start} : duration {self.turn_duration}  ...........")
                        self.audio_started = False
                        break
                    else:
                        if not self.audio_started:
                            logging.warning("Audio is started ...........")
                            self.audio_started = True
                            self.turn_start = time.monotonic()
                            self.turn_duration = len(data) / 2 / 24000
                        else:
                            self.turn_duration += len(data) / 2 / 24000

                    self._buffer.extend(data)
                except asyncio.QueueEmpty:
                    self._buffer.extend(b'\0' * missing)
                    #if self.audio_started:
                    #    logging.warning("No more audio while audio is playing 1")
                    break
            else:
                self._buffer.extend(b'\0' * missing)
                #if self.audio_started:
                #    logging.warning("No more audio while audio is playing 2")
                
        # Extract exactly one packet's worth of data.
        chunk = bytes(self._buffer[:self.chunk_size])
        self._buffer = self._buffer[self.chunk_size:]

        # Create a new audio frame.
        frame = AudioFrame(format="s16", layout="mono", samples=self.num_samples)
        try:
            frame.planes[0].update(chunk)
        except Exception:

            frame.planes[0].update(np.frombuffer(chunk, dtype="int16").tobytes())
        frame.sample_rate = self.sample_rate

        now = time.monotonic()

        if self._start_time is None:
            self._start_time = now

        frame_duration = self.num_samples / self.sample_rate  # e.g., 960/24000 = 0.04 sec
        scheduled_time = self._start_time + self._frame_index * frame_duration
        delay = scheduled_time - now

        if delay > 0:
            await asyncio.sleep(delay)

        frame.time_base = Fraction(1, self.sample_rate)
        frame.pts = self._frame_index * self.num_samples

        self._frame_index += 1

        return frame

async def offer(request):
    global current_pc
    params = await request.json()
    offer_desc = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # Define the STUN server
    stun_server = RTCIceServer(urls='stun:stun.l.google.com:19302')

    turn_server = RTCIceServer(
        urls=os.environ.get("TURN_SERVER_URLS").split(','),
        username=os.environ.get("TURN_SERVER_USERNAME"),
        credential=os.environ.get("TURN_SERVER_PASSWORD")
    )

    # Create the RTC configuration with the STUN server
    rtc_configuration = RTCConfiguration(iceServers=[turn_server, stun_server])

    # Initialize the RTCPeerConnection with the specified configuration
    pc = RTCPeerConnection(configuration=rtc_configuration)
    current_pc = pc
    pcs.add(pc)

    logging.info("Created RTCPeerConnection")

    @pc.on("icecandidate")
    async def on_icecandidate(candidate):
        if candidate:
            logging.info("New ICE candidate:", candidate.candidate)
            candidate_json = {
                "candidate": candidate.candidate,
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex,
            }
            if ws_client:
                try:
                    logging.info('send new candidate to remote')
                    await ws_client.send_str(json.dumps({
                        "type": "candidate",
                        "candidate": candidate_json,
                    }))
                except Exception as e:
                    logging.error("Error sending ICE candidate: %s", e)
        else:
            logging.info("ICE gathering complete")

    resampler = AudioResampler(format="s16", layout="mono", rate=24000)
    vad_resampler = AudioResampler(format="s16", layout="mono", rate=16000)
    vad_buffer = [] 

    @pc.on("track")
    async def on_track(track):
        logging.info("Received %s track from client", track.kind)
        if track.kind == "audio":
            async def process_audio():
                while True:
                    frame = await track.recv()
                    '''
                    vad_pcm_frames = vad_resampler.resample(frame)
                    if vad_pcm_frames:
                        vad_pcm_frame = vad_pcm_frames[0]
                        audio_bytes = vad_pcm_frame.to_ndarray().astype("int16").tobytes()
                        audio_samples = np.frombuffer(audio_bytes, dtype=np.int16)
                        audio_float = audio_samples.astype(np.float32) / 32768.0
                        vad_buffer.extend(audio_float.tolist())
                        if len(vad_buffer) >= int(16000 * 0.3):
                            speech_timestamps = get_speech_ts(
                                np.array(vad_buffer, dtype=np.float32),
                                vad_model,
                                threshold=0.5,
                                sampling_rate=16000
                            )
                            if speech_timestamps:
                                if turn_sequence.playing and not turn_sequence.paused:
                                    logging.info(f"New speech detected: {speech_timestamps}")
                                    turn_sequence.paused = True
                                # Here you can forward the buffered audio to your stream API or audio queue.
                                vad_buffer.clear()
                            else:
                                max_buffer = int(16000 * 2)  # keep at most 2 seconds
                                if len(vad_buffer) > max_buffer:
                                    vad_buffer[:] = vad_buffer[-int(16000 * 0.2):]
                    '''
                    if mic_muted:
                        continue
                    pcm_frames = resampler.resample(frame)
                    if pcm_frames:
                        pcm_frame = pcm_frames[0]
                        try:
                            audio_bytes = pcm_frame.planes[0].to_bytes()
                        except Exception:
                            audio_bytes = pcm_frame.to_ndarray().astype("int16").tobytes()
                        await llm_live_send_audio(audio_bytes)
                    else:
                        logging.error('resampler.resample: None')
            asyncio.create_task(process_audio())
            
        elif track.kind == "video":
            logging.info("Received video track from client; ignoring for now.")

        @track.on("ended")
        async def on_ended():
            print("Client %s track ended" % track.kind)

    #logging.info('====== remote offer ======')
    #logging.info(offer_desc)
    await pc.setRemoteDescription(offer_desc)

    audio_track = AudioTrack()
    pc.addTrack(audio_track)
    video_track = VideoTrack(fps=video_fps)
    pc.addTrack(video_track)

    answer = await pc.createAnswer()
    #logging.info('====== local answer ======')
    #logging.info(answer)
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }),
    )

async def websocket_handler(request):
    global ws_client, current_pc, mic_muted
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_client = ws
    logging.info("WebSocket web connection established")

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            data = msg.data.strip()
            try:
                data_json = json.loads(data)
                if data_json.get("type") == "candidate":
                    logging.info("Received ICE candidate: %s", data_json)
                    candidate = data_json.get("candidate")
                    if candidate and current_pc:
                        ice_candidate = RTCIceCandidate(
                            candidate["candidate"],
                            candidate["sdpMid"],
                            candidate["sdpMLineIndex"]
                        )
                        logging.info('new candidate from remote')
                        await current_pc.addIceCandidate(ice_candidate)
                elif data_json.get("type") == "text":
                    text_message = data_json.get("message")
                    logging.info("Received text message: %s", text_message)
                    await llm_live_send_text(text_message)
                elif data_json.get("type") == "predefined":
                    text_message = data_json.get("message")
                    logging.info("Received predefined message: %s", text_message)
                    if text_message.endswith('.wav') and ' ' not in text_message:
                        wave_file = text_message
                        await response_audio_wav(f"audios/{wave_file}")
                    else:
                        await llm_live_send_text(text_message, instructions=predefined_message_instructions)
                elif data_json.get("type") == "mic_mute":
                    mic_muted = data_json.get("muted", True)
                    logging.info("Received mic mute signal: %s", mic_muted)
                else:
                    logging.warning("Unknown message: %s", data)
            except Exception as e:
                logging.error("Error processing message: %s, error: %s", data, e)
        elif msg.type == web.WSMsgType.ERROR:
            logging.error("WebSocket closed with exception %s", ws.exception())

    logging.info("WebSocket connection closed")
    ws_client = None
    if current_pc:
        await current_pc.close()
        current_pc = None
    return ws

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def main():
    '''
    python -m scripts.live_chat --avatar frank --port 8008 --fps 12 --driver wav
    # remote must use https, or port forward to local
    http://127.0.0.1:21938/
    '''
    global video_fps, avatar, driver

    parser = argparse.ArgumentParser(
        description="WebRTC Streaming Prototype Server (Live Mode)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--fps", type=int, default=25, help="Frames per second for output video")
    parser.add_argument("--audio_buffer_time", type=int, default=3, help="Audio buffer time (seconds)")
    parser.add_argument("--avatar", type=str, required=True,
                        help="the avatar of the video file name without path and '.mp4'")
    parser.add_argument("--driver", type=str, default="openai",
                        help="openai or wav")
    args = parser.parse_args()
    video_fps = args.fps
    avatar = args.avatar
    driver = args.driver

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    app.router.add_get("/ws", websocket_handler)

    logging.info('run start_live_inference')
    avatar_video_file = f"data/video/{avatar}.mp4"
    init_live_inference(avatar_video_file)
    asyncio.create_task(start_live_inference(video_fps, args.audio_buffer_time))

    logging.info('run llm_live_listen')
    asyncio.create_task(llm_live_listen(driver=driver))

    logging.info('run web app')
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=args.host, port=args.port)
    await site.start()

    # Keep the main function running forever.
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())