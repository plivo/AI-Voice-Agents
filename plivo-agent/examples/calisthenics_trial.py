"""Answers a calisthenics studio's phone line and books a free trial class.

Serve:  python examples/calisthenics_trial.py
Then set your Plivo number's answer URL to PUBLIC_URL followed by /answer.
"""

import os

from loguru import logger
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService

from plivo_agent import Agent

PROMPT = """\
You answer the phone for Skyline Calisthenics. Your job is to book the caller a free trial class.
Trial classes run Monday to Saturday, at 7 in the morning and 6 in the evening.
Ask for the caller's name, then the day they want, then morning or evening.
When you have all three, call book_trial. After it succeeds, tell them it is booked and say goodbye."""


async def book_trial(params: FunctionCallParams, name: str, day: str, time: str) -> None:
    """Book a free trial class.

    Args:
        name: The caller's name.
        day: The day of the class, such as "Thursday".
        time: Either "7 AM" or "6 PM".
    """
    logger.info(f"Trial booked: {name}, {day} at {time}")  # your booking system goes here
    await params.result_callback({"booked": True})


agent = Agent(
    direction="inbound",
    prompt=PROMPT,
    public_url=os.environ["PUBLIC_URL"],
    tools=[book_trial],
    stt=lambda: DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"]),
    llm=lambda: OpenAILLMService(api_key=os.environ["OPENAI_API_KEY"]),
    tts=lambda: CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        settings=CartesiaTTSService.Settings(voice="86e30c1d-714b-4074-a1f2-1cb6b552fb49"),
    ),
)

if __name__ == "__main__":
    agent.run()
