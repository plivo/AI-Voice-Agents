# Deploy

The agent is one container. It keeps nothing between calls, so it needs no database and no disk. It needs a public HTTPS address that Plivo can reach, and it must stay running: a call arrives at any time.

## What every deployment needs

| Setting | Value |
|---|---|
| `PUBLIC_URL` | The https address of the server, with no path. Plivo's signature is checked against it. |
| `PLIVO_AUTH_TOKEN` | Your Plivo auth token. Load it from the platform's secret store. |
| `PLIVO_AUTH_ID` | Only for an agent that places calls. |
| Keys for your models | Whatever your agent file reads, such as `DEEPGRAM_API_KEY`. |
| `PORT` | The port to listen on. Most platforms set it. 8000 when unset. |
| Health check | `GET /health`, which answers 200. |
| Answer URL | In the Plivo console, set your number's answer URL to `PUBLIC_URL` followed by `/answer`, method POST. |

## Build the image

The `Dockerfile` at the root of this repository builds an image from one agent file. Name your file and the model providers it imports:

```sh
docker build --build-arg AGENT=my_agent.py --build-arg PROVIDERS=deepgram,openai,cartesia -t my-agent .
```

Left alone, it builds `examples/calisthenics_trial.py`. The agent file must call `agent.run()` with no port, so the platform's `PORT` is used.

## Run it with Docker

```sh
docker run --env-file .env -p 8000:8000 my-agent
```

`.env` holds the settings from the table above. On your own machine, `cloudflared tunnel --url http://localhost:8000` gives a public address for as long as it runs. Put that address in `PUBLIC_URL` before you start the container.

## Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/plivo/AI-Voice-Agents)

**Status.** Not yet deployed on a live Render account. The first deploy should check that the build finishes, that the service goes live on `/health`, and that a call to the number is answered.

The button reads `render.yaml` at the root of this repository: one web service built from the `Dockerfile` in this folder, which runs `examples/calisthenics_trial.py`. To run your own agent, fork the repository, change the example or the `AGENT` default in the `Dockerfile`, and point the button at your fork.

1. Press the button and sign in to Render.
2. Enter the four values the Blueprint asks for: `PLIVO_AUTH_TOKEN` and the three model keys the example reads.
3. Wait for the service to go live. Its address is `https://<name>.onrender.com`.
4. In the Plivo console, set your number's answer URL to that address followed by `/answer`.

| Setting | Value |
|---|---|
| `PUBLIC_URL` | Set by the start command from `RENDER_EXTERNAL_URL`, the service's own address |
| `PORT` | Set by Render. The agent listens on it |
| Health check path | `/health` |
| Plan | `starter`. The free plan sleeps after 15 minutes with no traffic and takes about a minute to wake, so the first call after a quiet spell fails |
| Automatic deploys | Off, so a push to the repository does not replace the container during a call |

## AWS

**Status.** `cfn-lint` passes on the template, but it has not yet been run against a live AWS account. The first run should check that the stack completes, that the task turns healthy, that a call is answered, and that the audio stream stays open through CloudFront for a whole call.

[`deploy/aws/template.yaml`](../deploy/aws/template.yaml) is a CloudFormation template for one agent: a Fargate task behind CloudFront and an internal Application Load Balancer. CloudFront's `*.cloudfront.net` address is the agent's HTTPS address and its `PUBLIC_URL`, so no domain or certificate is needed. The load balancer has no public address. The keys are stored in Secrets Manager.

1. Build the image and push it to ECR, in the Region you deploy to:

   ```sh
   aws ecr create-repository --repository-name plivo-agent
   REPO=$(aws ecr describe-repositories --repository-names plivo-agent --query "repositories[0].repositoryUri" --output text)
   aws ecr get-login-password | docker login --username AWS --password-stdin "${REPO%%/*}"
   docker build -t "$REPO:1" . && docker push "$REPO:1"
   ```

2. Create the stack:

   ```sh
   aws cloudformation deploy --stack-name plivo-agent --template-file deploy/aws/template.yaml \
     --capabilities CAPABILITY_IAM --parameter-overrides Image="$REPO:1" PlivoAuthToken=... \
     DeepgramApiKey=... OpenAiApiKey=... CartesiaApiKey=...
   aws cloudformation describe-stacks --stack-name plivo-agent --query "Stacks[0].Outputs"
   ```

3. In the Plivo console, set your number's answer URL to the `AnswerUrl` output.

- **Architecture.** The template runs ARM64, which is what `docker build` makes on Apple Silicon. For an image built on Intel or AMD, add `Architecture=X86_64`.
- **Other model providers.** The template names the three keys the example reads. For other providers, rename those parameters and the matching lines under `Keys` and `Task`.
- **Size and cost.** 1 vCPU and 2 GB. With the load balancer that is roughly $45 to $50 a month in us-east-1 before traffic, at AWS's list prices in November 2026. Check current prices.
- **A new version.** Push a new image tag and deploy the stack again with it. Calls on the old task end when it stops.

## Size

Measured on one container on an Apple Silicon laptop, with Deepgram, an OpenRouter model and ElevenLabs:

| State | Memory | CPU |
|---|---|---|
| No calls | about 100 MB | idle |
| 4 conversations at once | about 420 MB | about a third of one core |

Each conversation runs a voice detector and a turn model on the CPU. Start with 1 vCPU and 1 to 2 GB, and measure with your own models before you rely on more than a few calls per container.

## Logs

The agent logs one line when a call connects and one when it ends. It does not log the prompt or what is said. Set `LOGURU_LEVEL=DEBUG` to see Pipecat's full output while you debug: that output includes everything the caller says, so keep it off in production.

## What to know before real traffic

- **A new deploy ends live calls.** When the platform replaces the container, calls on the old one drop. Deploy at a quiet time.
- **The agent must not sleep.** A platform that stops idle containers will miss the first call.
- **More than one container is fine.** Each call stays on the container that accepted its stream, and containers share nothing.
