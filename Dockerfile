FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/

COPY client/ ./client/

RUN mkdir -p /app/uploads

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
