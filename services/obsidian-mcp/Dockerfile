FROM python:3.12-slim

WORKDIR /app

COPY app ./app

ENV MCP_PORT=8090
ENV OBSIDIAN_VAULT_ROOT=/vault

EXPOSE 8090

CMD ["python", "-m", "app.main"]
