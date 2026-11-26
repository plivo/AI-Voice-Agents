"""A call from Plivo's side: the answer XML, then the agent's first words coming back as Plivo audio."""

import json
import sys
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from loguru import logger
from pipecat.frames.frames import (
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TTSAudioRawFrame,
)
from pipecat.services.llm_service import LLMService
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService

from plivo_agent import VOICE_RULES, Agent
from plivo_agent.signature import sign

PLIVO_START = {"event": "start", "start": {"streamId": "stream-1", "callId": "call-1"}}


class SilentSTT(STTService):
    async def run_stt(self, audio):
        return
        yield


class ScriptedLLM(LLMService):
    """Says one line whenever it is asked for a reply, and records what it was asked."""

    asked: ClassVar[list] = []

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if not isinstance(frame, LLMContextFrame):
            return await self.push_frame(frame, direction)
        self.asked.append(frame.context.get_messages())
        for reply in (
            LLMFullResponseStartFrame(),
            LLMTextFrame("Hello, this is the clinic."),
            LLMFullResponseEndFrame(),
        ):
            await self.push_frame(reply)


class ToneTTS(TTSService):
    said: ClassVar[list] = []

    async def run_tts(self, text, context_id):
        self.said.append(text)
        yield TTSAudioRawFrame(audio=b"\x00\x01" * 800, sample_rate=8000, num_channels=1, context_id=context_id)


def make_agent(direction):
    return Agent(
        prompt="Confirm the appointment.",
        direction=direction,
        public_url="https://bot.test",
        stt=SilentSTT,
        llm=ScriptedLLM,
        tts=ToneTTS,
    )


def signed(url, form=()):
    """The headers Plivo would put on a request to this address."""
    return {
        "x-plivo-signature-v3": sign("auth-token", url, "nonce-1", form=form),
        "x-plivo-signature-v3-nonce": "nonce-1",
    }


STREAM_SIGNED = signed("http://bot.test/ws")


@pytest.fixture(autouse=True)
def plivo_credentials(monkeypatch):
    monkeypatch.setenv("PLIVO_AUTH_ID", "auth-id")
    monkeypatch.setenv("PLIVO_AUTH_TOKEN", "auth-token")


@pytest.fixture
def agent():
    return make_agent("inbound")


def test_the_answer_tells_plivo_to_stream_the_call_to_the_public_address(agent):
    call = {"To": "+14155550100", "CallUUID": "call-1"}
    headers = signed("https://bot.test/answer", form=call.items())

    answer = TestClient(agent.app).post("/answer", data=call, headers=headers)

    assert 'contentType="audio/x-mulaw;rate=8000"' in answer.text
    assert ">wss://bot.test/ws</Stream>" in answer.text


def test_a_served_agent_does_not_log_what_is_said_on_calls(agent, monkeypatch, capsys):
    monkeypatch.setattr("uvicorn.run", lambda *_, **__: None)
    monkeypatch.delenv("LOGURU_LEVEL", raising=False)
    logger.add(sys.stderr, level="DEBUG")  # what loguru does by default

    agent.run()
    logger.debug("Transcription: my card number is 4111")
    logger.info("Call call-1 connected")

    logged = capsys.readouterr().err
    logger.remove()
    assert "4111" not in logged
    assert "Call call-1 connected" in logged


def test_a_host_platform_can_check_the_agent_is_up_without_a_signature(agent):
    assert TestClient(agent.app).get("/health").status_code == 200


@pytest.mark.parametrize("headers", [{}, signed("https://someone-else.test/answer")])
def test_a_request_plivo_did_not_sign_gets_no_answer_and_no_call(agent, headers):
    plivo = TestClient(agent.app)

    assert plivo.post("/answer", headers=headers).status_code == 403
    with pytest.raises(WebSocketDisconnect), plivo.websocket_connect("/ws", headers=headers):
        pass


# Expected values were accepted by validate_v3_signature in Plivo's own Python SDK.
@pytest.mark.parametrize(
    ("query", "form", "expected"),
    [
        ([("b", "2"), ("a", "1")], [], "iWbVOK9DexoMo72dZBtAzApvPjDHrXVUc9eej/YDPZU="),
        ([], [("To", "+14155550100"), ("CallUUID", "c-1")], "JvCVe7opRuZ0lYXcNLpcvC3AX5HiEfQW/NZ8DclPnWk="),
        (
            [("leg", "in")],
            [("To", "+14155550100"), ("From", "+14065550199"), ("CallUUID", "c-1")],
            "5rUx1gaTsrDtTieC8ueG9iSMudaahnNZfQKW8Axqk6E=",
        ),
    ],
)
def test_the_signature_matches_plivos_own(query, form, expected):
    assert sign("test-token", "https://bot.test/answer", "12345", query, form) == expected


def test_the_prompt_follows_the_voice_rules(agent):
    assert agent._instructions == f"{VOICE_RULES}\n\nConfirm the appointment."


def test_dialing_without_a_plivo_credential_names_the_missing_one(monkeypatch):
    monkeypatch.delenv("PLIVO_AUTH_ID")

    with pytest.raises(KeyError, match="PLIVO_AUTH_ID"):
        make_agent("outbound").call("+14155550100", from_number="+14065550199")


@pytest.mark.parametrize(
    ("direction", "told", "first_words"),
    [
        ("inbound", "This person has just called you.", "Hello, thanks for calling."),
        ("outbound", "You have just called this person.", "Hello!"),
    ],
)
def test_the_agent_speaks_first_knowing_who_called_whom(direction, told, first_words):
    ToneTTS.said.clear()
    with TestClient(make_agent(direction).app).websocket_connect("/ws", headers=STREAM_SIGNED) as plivo:
        plivo.send_json(PLIVO_START)
        plivo.send_json({"event": "media", "media": {"payload": ""}})

        played = plivo.receive_json()

    assert ScriptedLLM.asked[-1][0]["content"].startswith(told)
    assert ToneTTS.said[0] == first_words
    assert f'You have already said "{first_words}"' in ScriptedLLM.asked[-1][0]["content"]
    assert played["event"] == "playAudio"
    assert played["media"]["contentType"] == "audio/x-mulaw"
    assert played["streamId"] == "stream-1"


def test_an_outbound_agent_asks_plivo_to_dial(monkeypatch):
    sent = {}

    class Accepted:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"request_uuid": "req-1"}'

    def open_request(request, timeout):
        sent.update(url=request.full_url, body=json.loads(request.data), authorization=request.headers["Authorization"])
        return Accepted()

    monkeypatch.setattr("urllib.request.urlopen", open_request)

    request_id = make_agent("outbound").call("+14155550100", from_number="+14065550199")

    assert request_id == "req-1"
    assert sent["url"] == "https://api.plivo.com/v1/Account/auth-id/Call/"
    assert sent["body"] == {"to": "+14155550100", "from": "+14065550199", "answer_url": "https://bot.test/answer"}
    assert sent["authorization"] == "Basic YXV0aC1pZDphdXRoLXRva2Vu"


def test_an_inbound_agent_refuses_to_dial():
    with pytest.raises(ValueError, match="outbound"):
        make_agent("inbound").call("+14155550100", from_number="+14065550199")
