#!/bin/bash

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Create required directories
mkdir -p logs
mkdir -p detected_texts
mkdir -p recordings

# Install system dependencies for tesseract
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install tesseract
fi

# Setup configuration
if [ ! -f config.yaml ]; then
    cp config.yaml.example config.yaml
fi

echo "Installation complete!"