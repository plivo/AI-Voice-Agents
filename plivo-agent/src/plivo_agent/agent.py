"""A Plivo phone agent: your speech, language and voice models, wired into one working call."""

import base64
import json
import os
import sys
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl

import uvicorn
from fastapi import FastAPI, Request, Response, WebSocket
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndWorkerFrame, FunctionCallResultProperties, LLMMessagesAppendFrame, TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMUserAggregatorParams
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.services.llm_service import FunctionCallParams, LLMService
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.turns.user_mute import MuteUntilFirstBotCompleteUserMuteStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from plivo_agent.signature import is_from_plivo

# What every phone agent is told before its own prompt. Pass Agent(voice_rules=...) to replace it.
VOICE_RULES = (Path(__file__).parent / "voice_rules.md").read_text(encoding="utf-8").strip()
# The only two things that differ between an inbound and an outbound call.
OPENING_LINE = {"inbound": "Hello, thanks for calling.", "outbound": "Hello!"}
WHO_CALLED = {"inbound": "This person has just called you.", "outbound": "You have just called this person."}
# Told to the model while the opening line plays, so it does not greet twice.
CALL_CONNECTED = '{who_called} You have already said "{opening}". Now carry on as your instructions say.'
PLIVO_CALLS = "https://api.plivo.com/v1/Account/{auth_id}/Call/"
ANSWER_PATH = "/answer"
HEALTH_PATH = "/health"
STREAM_PATH = "/ws"
# Plivo's reply to "what do I do with this call": stream both directions of its audio to us.
ANSWER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">{stream_url}</Stream>
</Response>"""


async def end_call(params: FunctionCallParams) -> None:
    """End the phone call. Call this only after you have said goodbye."""
    await params.result_callback(None, properties=FunctionCallResultProperties(run_llm=False))
    # Sent downstream so the goodbye already on its way to the caller is played before the call ends.
    await params.llm.push_frame(EndWorkerFrame())


class Agent:
    """One phone agent that either answers calls or places them. Each call gets its own models, so pass functions that build them.

    public_url is the https address Plivo reaches this server at. PLIVO_AUTH_TOKEN must be set: it proves a request is Plivo's.
    """

    def __init__(
        self,
        *,
        prompt: str,
        direction: Literal["inbound", "outbound"],
        public_url: str,
        stt: Callable[[], STTService],
        llm: Callable[[], LLMService],
        tts: Callable[[], TTSService],
        tools: Sequence[Callable] = (),
        turn_strategies: UserTurnStrategies | None = None,
        voice_rules: str = VOICE_RULES,
    ) -> None:
        self._instructions = f"{voice_rules}\n\n{prompt}"
        self._direction = direction
        self._public_url = public_url.rstrip("/")
        self._auth_token = os.environ["PLIVO_AUTH_TOKEN"]
        self._opening_line = OPENING_LINE[direction]
        told = CALL_CONNECTED.format(who_called=WHO_CALLED[direction], opening=self._opening_line)
        self._call_connected = {"role": "developer", "content": told}
        self._build_stt, self._build_llm, self._build_tts = stt, llm, tts
        self._tools = [end_call, *tools]
        self._turn_strategies = turn_strategies
        self.app = self._build_app()

    def run(self, host: str = "0.0.0.0", port: int | None = None) -> None:
        """Serve calls until the process is stopped, on the port the host platform names in PORT, or 8000."""
        logger.remove()
        # Pipecat's DEBUG lines carry the prompt and everything the caller says, so they are off unless asked for.
        logger.add(sys.stderr, level=os.environ.get("LOGURU_LEVEL", "INFO"))
        uvicorn.run(self.app, host=host, port=port or int(os.environ.get("PORT", "8000")))

    def call(self, to: str, *, from_number: str) -> str:
        """Dial a number and return Plivo's id for the request. The agent must be running at its public_url."""
        if self._direction != "outbound":
            raise ValueError('only an agent made with direction="outbound" can place a call')
        auth_id = os.environ["PLIVO_AUTH_ID"]
        credentials = base64.b64encode(f"{auth_id}:{self._auth_token}".encode()).decode()
        request = urllib.request.Request(
            PLIVO_CALLS.format(auth_id=auth_id),
            data=json.dumps({"to": to, "from": from_number, "answer_url": self._public_url + ANSWER_PATH}).encode(),
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)["request_uuid"]

    def _build_app(self) -> FastAPI:
        app = FastAPI()

        address = self._public_url.split("://", 1)[1]
        # Plivo signs the stream's address as http, whatever scheme the stream itself uses.
        stream_urls = [f"{scheme}://{address}{STREAM_PATH}" for scheme in ("http", "https")]

        @app.get(HEALTH_PATH)
        async def health() -> Response:
            return Response("ok")

        @app.api_route(ANSWER_PATH, methods=["GET", "POST"])
        async def answer(request: Request) -> Response:
            query = parse_qsl(request.scope["query_string"].decode(), keep_blank_values=True)
            form = parse_qsl((await request.body()).decode(), keep_blank_values=True)
            if not is_from_plivo(self._auth_token, [self._public_url + ANSWER_PATH], request.headers, query, form):
                return Response("not signed by Plivo", status_code=403)
            xml = ANSWER_XML.format(stream_url=f"wss://{address}{STREAM_PATH}")
            return Response(xml, media_type="application/xml")

        @app.websocket(STREAM_PATH)
        async def stream(websocket: WebSocket) -> None:
            if not is_from_plivo(self._auth_token, stream_urls, websocket.headers):
                return await websocket.close(code=1008)
            await websocket.accept()
            await self._talk(websocket)

        return app

    async def _talk(self, websocket: WebSocket) -> None:
        """Hold one call from Plivo's first message to the hang-up."""
        transport = await self._plivo_transport(websocket)
        worker = PipelineWorker(self._pipeline(transport))
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)

        @transport.event_handler("on_client_connected")
        async def open_the_call(_transport, _client) -> None:
            thinks_meanwhile = LLMMessagesAppendFrame([self._call_connected], run_llm=True)
            await worker.queue_frames([TTSSpeakFrame(self._opening_line), thinks_meanwhile])

        @transport.event_handler("on_client_disconnected")
        async def stop(_transport, _client) -> None:
            await runner.cancel()

        await runner.run()
        logger.info("Call ended")

    async def _plivo_transport(self, websocket: WebSocket) -> FastAPIWebsocketTransport:
        provider, call = await parse_telephony_websocket(websocket)
        if provider != "plivo":
            raise ValueError(f"expected a Plivo audio stream, got {provider!r}")
        logger.info(f"Call {call['call_id']} connected")
        # Plivo ends the call itself once this stream closes, so no hang-up request is needed.
        hands_off = PlivoFrameSerializer.InputParams(auto_hang_up=False)
        serializer = PlivoFrameSerializer(stream_id=call["stream_id"], params=hands_off)
        params = FastAPIWebsocketParams(audio_in_enabled=True, audio_out_enabled=True, serializer=serializer)
        return FastAPIWebsocketTransport(websocket, params)

    def _pipeline(self, transport: FastAPIWebsocketTransport) -> Pipeline:
        llm = self._build_llm()
        llm.append_system_instruction(self._instructions)
        listening = LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            user_turn_strategies=self._turn_strategies,
            # A caller who says "hello?" into the opening silence would cancel the agent's first line.
            user_mute_strategies=[MuteUntilFirstBotCompleteUserMuteStrategy()],
        )
        caller, agent = LLMContextAggregatorPair(LLMContext(tools=self._tools), user_params=listening)
        return Pipeline(
            [transport.input(), self._build_stt(), caller, llm, self._build_tts(), transport.output(), agent]
        )
