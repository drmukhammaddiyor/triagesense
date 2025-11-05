# Dockerfile — production friendly with entrypoint normalization (handles CRLF -> LF)
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

# Normalize line endings and make entrypoint executable (fix Windows -> Linux script issues)
# This converts CRLF to LF and ensures the script is executable inside the image
RUN if [ -f /app/entrypoint.sh ]; then sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh; fi

# Expose port
EXPOSE 8000

# Use the entrypoint script (it handles empty PORT and starts gunicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
