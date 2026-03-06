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

    async def run(self):
        """Main entry: connect to orchestrator, process audio from existing room."""
        logger.info(f"Starting worker for session {self.session_id}")

        # Connect to orchestrator WS
        orch_url = f"{self.orchestrator_url}/ws/session/{self.session_id}"
        try:
            self._ws = await websockets.connect(orch_url)
            logger.info("Connected to orchestrator")
        except Exception as e:
            logger.error(f"Failed to connect to orchestrator: {e}")
            return

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
            # Notify orchestrator
            await self._send_event("client.audio.started", {})
            logger.info("Worker fully connected and listening.")

            # Keep running
            while True:
                await asyncio.sleep(1)

        finally:
            if self._ws:
                await self._ws.close()

    async def _process_audio_track(self, track: rtc.Track):
        """Process incoming audio track frames."""
        audio_stream = rtc.AudioStream(track)

        async for frame_event in audio_stream:
            frame = frame_event.frame
            pcm_data = bytes(frame.data)

            vad_result = self.vad.process_frame(pcm_data)

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
                asyncio.create_task(self._transcribe_and_send(all_audio, frame.sample_rate))

    async def _transcribe_and_send(self, pcm_data: bytes, sample_rate: int):
        """Convert PCM to WAV, transcribe with Whisper, send to orchestrator."""
        try:
            # Convert PCM to WAV
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(1)
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
        """Send event to orchestrator via WebSocket."""
        if self._ws:
            event = {
                "type": event_type,
                "session_id": self.session_id,
                "payload": payload,
            }
            await self._ws.send(json.dumps(event))


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
