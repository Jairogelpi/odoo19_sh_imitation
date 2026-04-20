FROM python:3.12-slim

WORKDIR /app

COPY app ./app

ENV MCP_PORT=8092
ENV CONTEXT7_DOCS_ROOT=/docs

EXPOSE 8092

CMD ["python", "-m", "app.main"]
