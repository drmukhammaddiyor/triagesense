# Dockerfile — production friendly using python slim and entrypoint wrapper
FROM python:3.11-slim

# Set env
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# System deps
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Copy requirements first (cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Use the entrypoint script (it handles empty PORT and starts gunicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
