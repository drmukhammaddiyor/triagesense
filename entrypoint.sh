#!/bin/sh
# entrypoint.sh — ensure PORT is valid then start gunicorn

# If PORT is unset or empty, default to 8000
if [ -z "" ] || [ "" = "''" ]; then
  export PORT=8000
fi

echo "Starting Gunicorn on port: "
exec gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0: --workers 2 --threads 2
