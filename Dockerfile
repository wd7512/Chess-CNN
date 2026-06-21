FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

WORKDIR /app

# Install system deps for OpenCV headless
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.docker.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy application code
COPY . .

# Create output directories
RUN mkdir -p /app/screenshots /app/logs /app/output

# Smoke test entry
COPY tools/docker_smoke_test.py /app/docker_smoke_test.py

CMD ["python", "docker_smoke_test.py"]
