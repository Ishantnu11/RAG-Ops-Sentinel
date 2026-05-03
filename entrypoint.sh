#!/bin/bash

# Start Ollama in the background
echo "Starting Ollama..."
ollama serve &

# Wait for Ollama to start
sleep 7

# Pull the model (this might take a minute on the first run)
echo "Pulling llama3.2..."
ollama pull llama3.2

# Start Streamlit on Hugging Face's default port 7860
echo "Starting Streamlit on port 7860..."
streamlit run app.py --server.port 7860 --server.address 0.0.0.0
