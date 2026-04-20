FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV MCP_PORT=8094

EXPOSE 8094

CMD ["python", "-m", "app.main"]
