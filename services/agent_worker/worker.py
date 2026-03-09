"""
Agent worker — connects to LiveKit room, captures audio, transcribes via Whisper,
and relays transcripts to the orchestrator via WebSocket.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import wave

from dotenv import load_dotenv

load_dotenv()

import websockets
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, JobRequest, WorkerOptions, cli, JobProcess

from stt import transcribe
from vad import VoiceActivityDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("maya-agent")
logger = logging.getLogger("agent_worker")


class AgentWorker:
    """LiveKit participant that captures audio, runs VAD + STT, relays to orchestrator."""

    def __init__(self, room: rtc.Room, session_id: str):
        self.session_id = session_id
        self.orchestrator_url = os.getenv("ORCHESTRATOR_WS_URL", "ws://localhost:8000")
        self.vad = VoiceActivityDetector()
        self._audio_buffer: list[bytes] = []
        self._ws = None
        self._room = room
        self._reader_task: asyncio.Task | None = None

    async def run(self):
        """Main entry: connect to orchestrator, process audio from existing room."""
        logger.info(f"Starting worker for session {self.session_id}")

        @self._room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(f"Subscribed to audio track from {participant.identity}")
                asyncio.create_task(self._process_audio_track(track))

        # Check for any tracks that were already published before we joined
        for participant in self._room.remote_participants.values():
            for track_publication in participant.track_publications.values():
                if track_publication.track and track_publication.track.kind == rtc.TrackKind.KIND_AUDIO:
                    logger.info(f"Found existing audio track from {participant.identity}")
                    asyncio.create_task(self._process_audio_track(track_publication.track))

        try:
            # Connect to orchestrator and start the background reader
            await self._connect_and_notify()

            # Keep the coroutine alive; LiveKit will cancel us when the room ends
            await asyncio.Event().wait()

        finally:
            if self._reader_task:
                self._reader_task.cancel()
            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass


    async def _connect_and_notify(self):
        """Connect to orchestrator, send initial ready event, and start background reader."""
        orch_url = f"{self.orchestrator_url}/ws/session/{self.session_id}"
        try:
            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass
            self._ws = await websockets.connect(orch_url)
            logger.info("Connected to orchestrator")
            # Start background reader so the websockets library can service server pings
            if self._reader_task:
                self._reader_task.cancel()
            self._reader_task = asyncio.create_task(self._ws_reader())
            await self._send_event("client.audio.started", {})
            logger.info("Worker fully connected and listening.")
        except Exception as e:
            logger.error(f"Failed to connect to orchestrator: {e}")

    async def _ws_reader(self):
        """Background task: drain inbound WebSocket messages.
        
        This is required for the websockets library to service server-sent
        ping frames and reply with pong frames. Without this, the server closes
        the connection with code 1011 (keepalive ping timeout).
        """
        try:
            async for message in self._ws:
                # We receive nothing useful from the server in this direction,
                # but we must keep reading to service keepalive pings.
                pass
        except Exception:
            pass

    async def _process_audio_track(self, track: rtc.Track):
        """Process incoming audio track frames."""
        audio_stream = rtc.AudioStream(track)
        frame_count = 0

        async for frame_event in audio_stream:
            frame = frame_event.frame
            pcm_data = bytes(frame.data)
            frame_count += 1
            duration_ms = (len(pcm_data) / 2 / frame.num_channels) / frame.sample_rate * 1000.0

            # Log periodically to confirm frames are flowing
            if frame_count % 500 == 0:
                logger.info(f"[AUDIO] Received {frame_count} frames. sr={frame.sample_rate} ch={frame.num_channels} pcm_len={len(pcm_data)}")

            vad_result = self.vad.process_frame(pcm_data, duration_ms)

            if vad_result == "speech_start":
                self._audio_buffer = [pcm_data]
                asyncio.create_task(self._send_event("client.speech.started", {}))
            elif self.vad.is_speaking:
                self._audio_buffer.append(pcm_data)
            elif vad_result == "speech_end":
                self._audio_buffer.append(pcm_data)
                # Combine buffer and transcribe
                all_audio = b"".join(self._audio_buffer)
                self._audio_buffer = []
                asyncio.create_task(self._transcribe_and_send(all_audio, frame.sample_rate, frame.num_channels))

    async def _transcribe_and_send(self, pcm_data: bytes, sample_rate: int, num_channels: int):
        """Convert PCM to WAV, transcribe with Whisper, send to orchestrator."""
        try:
            # Convert PCM to WAV
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(num_channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(pcm_data)
            wav_bytes = wav_buffer.getvalue()

            # Send partial indicator
            await self._send_event("client.transcript.partial", {"text": "..."})

            # Transcribe
            text = await transcribe(wav_bytes)

            if text and text.strip():
                logger.info(f"Transcript: {text}")
                await self._send_event("client.transcript.final", {"text": text})

        except Exception as e:
            logger.error(f"Transcription error: {e}")

    async def _send_event(self, event_type: str, payload: dict):
        """Send event to orchestrator via WebSocket with auto-reconnect."""
        event = {
            "type": event_type,
            "session_id": self.session_id,
            "payload": payload,
        }
        event_str = json.dumps(event)
        
        for attempt in range(3):
            try:
                if not self._ws:
                    orch_url = f"{self.orchestrator_url}/ws/session/{self.session_id}"
                    self._ws = await websockets.connect(orch_url)
                    # Restart the background reader after reconnect
                    if self._reader_task:
                        self._reader_task.cancel()
                    self._reader_task = asyncio.create_task(self._ws_reader())
                    logger.info("Reconnected to orchestrator for STT send")
                    
                await self._ws.send(event_str)
                return
            except Exception as e:
                logger.warning(f"WS send error (attempt {attempt+1}): {e}")
                self._ws = None
                await asyncio.sleep(0.5)


async def entrypoint(ctx: JobContext):
    """Entrypoint for LiveKit Cloud deployment."""
    # Connect to the room (auto-subscribing to audio tracks)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # The room name is our session_id
    session_id = ctx.room.name
    
    worker = AgentWorker(ctx.room, session_id)
    await worker.run()


async def request_fnc(req: JobRequest) -> None:
    """Accept incoming job requests automatically."""
    logger.info(f"Accepting job for room {req.room.name}")
    await req.accept()


if __name__ == "__main__":
    import sys
    # If run with a session ID locally, we could mock the JobContext but it's simpler
    # to use the standard cli.run_app which connects to the configured LIVEKIT_URL
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        request_fnc=request_fnc,
    ))
