"""Calls a patient to confirm an appointment.

Serve:  python examples/appointment.py
Dial:   python examples/appointment.py +14155550100   (needs PLIVO_NUMBER and PLIVO_AUTH_ID)
"""

import os
import sys

from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService

from plivo_agent import Agent

agent = Agent(
    direction="outbound",
    public_url=os.environ["PUBLIC_URL"],
    prompt="You are calling from a dental clinic to confirm the caller's appointment for tomorrow at 10 AM. If they cannot come, ask which day suits them.",
    stt=lambda: DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"]),
    llm=lambda: OpenAILLMService(api_key=os.environ["OPENAI_API_KEY"]),
    tts=lambda: CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        settings=CartesiaTTSService.Settings(voice="86e30c1d-714b-4074-a1f2-1cb6b552fb49"),
    ),
)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        agent.run()
    else:
        agent.call(sys.argv[1], from_number=os.environ["PLIVO_NUMBER"])
