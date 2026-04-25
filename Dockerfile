# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=6006

# Install system dependencies for Scrapling/Playwright and Ollama
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (needed by Scrapling/Patchright)
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Create directory for persistent data (used if no volume is mounted)
RUN mkdir -p /app/data/chroma_db /app/data/phoenix_data

# Expose the port Phoenix will run on
EXPOSE 6006

# Create start script
RUN echo '#!/bin/bash\n\
ollama serve & \n\
sleep 5\n\
echo "Pulling Llama 3.2 model..."\n\
ollama pull llama3.2\n\
echo "Launching Phoenix Dashboard..."\n\
python launch_phoenix.py' > /app/start.sh
RUN chmod +x /app/start.sh

# Default command
CMD ["/app/start.sh"]
