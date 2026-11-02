FROM node:22-bookworm-slim

# Build one backend per image. Versions must be supplied by the operator, never "latest".
ARG AGENT_BACKEND
ARG CLI_VERSION
RUN test -n "$CLI_VERSION" && test "$CLI_VERSION" != "latest" \
    && printf '%s' "$CLI_VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.-]+)?$' \
    && case "$AGENT_BACKEND" in \
         codex) npm install --global --ignore-scripts "@openai/codex@$CLI_VERSION" ;; \
         claude_code) npm install --global "@anthropic-ai/claude-code@$CLI_VERSION" ;; \
         *) exit 1 ;; \
       esac \
    && npm cache clean --force

RUN apt-get update \
    && apt-get install --yes --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 agent-runner \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent agent-runner \
    && mkdir -p /opt/agent-runner /var/lib/agent-runner \
    && chown 10001:10001 /var/lib/agent-runner \
    && chmod 700 /var/lib/agent-runner

COPY requirements.txt /opt/agent-runner/requirements.txt
RUN python3 -m venv /opt/agent-runner/venv \
    && /opt/agent-runner/venv/bin/pip install --no-cache-dir -r /opt/agent-runner/requirements.txt
COPY server.py /opt/agent-runner/server.py

ENV AGENT_RUNNER_BACKEND=$AGENT_BACKEND \
    AGENT_RUNNER_ISOLATED=true \
    AGENT_RUNNER_STATE_PATH=/var/lib/agent-runner/requests.sqlite3 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /opt/agent-runner
USER 10001:10001
EXPOSE 8091
VOLUME ["/var/lib/agent-runner"]
CMD ["/opt/agent-runner/venv/bin/uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8091", "--no-access-log", "--log-level", "critical"]
