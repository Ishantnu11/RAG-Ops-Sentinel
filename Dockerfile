# Use Python 3.10
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -L https://ollama.com/download/ollama-linux-amd64 -o /usr/bin/ollama \
    && chmod +x /usr/bin/ollama

# Set up user and directory
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=user . .

# Hugging Face Spaces uses port 7860
EXPOSE 7860

# Set permissions for entrypoint
RUN chmod +x entrypoint.sh

# Start the application
CMD ["./entrypoint.sh"]
