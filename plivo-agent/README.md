# plivo-agent

A working Plivo phone agent on [Pipecat](https://github.com/pipecat-ai/pipecat). You choose the speech-to-text, language and voice models and write a short prompt. The package answers the call, runs the conversation and hangs up.

## Quickstart

Needs Python 3.12 or later.

```bash
pip install plivo-agent "pipecat-ai[deepgram,openai,cartesia]"
export PLIVO_AUTH_TOKEN=...                 # every agent
export PLIVO_AUTH_ID=...                    # outbound agents only
export PUBLIC_URL=https://your-server.example.com
export DEEPGRAM_API_KEY=... OPENAI_API_KEY=... CARTESIA_API_KEY=...
python examples/appointment.py
```

The server needs a public HTTPS address, given as `public_url`. In the Plivo console, set your number's answer URL to that address followed by `/answer`. Then call the number.

```python
agent = Agent(
    direction="outbound",
    public_url="https://your-server.example.com",
    prompt="You are calling from a dental clinic to confirm the caller's appointment for tomorrow at 10 AM.",
    stt=lambda: DeepgramSTTService(api_key=...),
    llm=lambda: OpenAILLMService(api_key=...),
    tts=lambda: CartesiaTTSService(api_key=..., settings=...),
)
agent.run()
```

`stt`, `llm` and `tts` are functions because every call needs its own copy of each model.

## Inbound or outbound

`direction` is required.

- `"inbound"`: the agent answers calls. Set your Plivo number's answer URL to `public_url` followed by `/answer`.
- `"outbound"`: the agent places calls. Keep the server running, then dial:

```python
agent.call("+14155550100", from_number="+14065550199")
```

## Only Plivo can reach the agent

Plivo signs every request with your auth token. The agent checks that signature on the answer URL and on the audio stream, and refuses anything else, so a stranger who finds the address cannot start a conversation on your bill. The check uses `public_url`, so it must be the exact address Plivo calls.

## Examples

| File | Direction | What the agent does |
|---|---|---|
| `examples/appointment.py` | outbound | Calls a patient to confirm an appointment. |
| `examples/calisthenics_trial.py` | inbound | Answers a studio's line and books a free trial class through a tool. |

## Options

| Argument | What it does |
|---|---|
| `tools` | Your own functions the agent may call, written as Pipecat direct functions. |
| `turn_strategies` | How the agent decides the caller has finished speaking. Defaults to Pipecat's local smart-turn model. |
| `voice_rules` | The rules every phone agent is given before your prompt. See `voice_rules.md`. |

## Deploy

The agent runs as one container with no database. [docs/deploy.md](docs/deploy.md) has the settings, the `Dockerfile` usage, a Render button, an AWS template and measured sizes.

## Status

Version 0.1.0 is an early release. Inbound and outbound calls have been run on live Plivo numbers.
