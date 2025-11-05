# Use tiangolo image built for FastAPI (production-ready)
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Copy project
COPY . /app

# Install dependencies (uses requirements.txt)
RUN pip install --no-cache-dir -r /app/requirements.txt

# Ensure working dir
WORKDIR /app

# Expose port (Render/others forward to 8000 by default)
EXPOSE 8000

# Use the default entrypoint from the image (uvicorn/gunicorn)
