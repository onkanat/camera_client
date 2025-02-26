#!/bin/bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# Install system dependencies
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr python3-tk
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install tesseract
fi

# Create required directories
mkdir -p detected_texts logs recordings

echo "Kurulum tamamlandı!"lum tamamlandı!"