FROM python:3.12-slim

WORKDIR /app

COPY app ./app

ENV MCP_PORT=8091
ENV MEMORY_STORE_FILE=/data/memory_store.json

EXPOSE 8091

CMD ["python", "-m", "app.main"]
