#!/bin/bash

# Start Ollama in the background
echo "Starting Ollama..."
ollama serve &

# Wait for Ollama to start
sleep 5

# Pull the required model
echo "Pulling llama3.2..."
ollama pull llama3.2

# Start the Streamlit app
echo "Starting Streamlit..."
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
