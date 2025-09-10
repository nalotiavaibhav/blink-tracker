# Simple production image for the WaW FastAPI backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps for bcrypt (if needed) and clean up
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Install only backend dependencies (avoid desktop libs like PyQt/MediaPipe in the image)
COPY requirements.backend.txt /app/
RUN pip install --no-cache-dir -r requirements.backend.txt

COPY . /app

EXPOSE 8000

# Use uvicorn directly; for higher load, consider gunicorn with uvicorn workers
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
