# Dockerfile — run gunicorn via inline sh to avoid external script exec issues
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

# Use a small inline shell to ensure PORT is valid then start gunicorn
ENTRYPOINT ["sh", "-c", "if [ -z \"\" ] || [ \"\" = \"''\" ]; then export PORT=8000; fi; echo Starting Gunicorn on port: ; exec gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0: --workers 2 --threads 2"]
