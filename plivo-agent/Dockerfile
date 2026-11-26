# One phone agent in a container. Build with your own agent file and model providers:
#   docker build --build-arg AGENT=my_agent.py --build-arg PROVIDERS=deepgram,openai,cartesia -t my-agent .
FROM python:3.12-slim
ARG AGENT=examples/calisthenics_trial.py
ARG PROVIDERS=deepgram,openai,cartesia
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . "pipecat-ai[${PROVIDERS}]" && useradd --system --create-home agent
COPY ${AGENT} agent.py
USER agent
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/health')"
CMD ["python", "agent.py"]
