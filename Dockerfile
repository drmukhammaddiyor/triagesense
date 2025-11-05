# Dockerfile — production friendly using python slim and gunicorn + uvicorn workers
FROM python:3.11-slim

# Set env
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy requirements first (cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

# Expose port
EXPOSE 8000

# Start command: use gunicorn + uvicorn workers, bind to PORT env set by Render
CMD exec gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0: --workers 2 --threads 2
