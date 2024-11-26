#!/bin/bash

# Update package lists
apt-get update

# Install required packages
apt-get install -y \
    python3 \
    python3-pip \
    python3-opencv \
    python3-picamera2 \
    python3-libcamera \
    python3-numpy \
    pigpio \
    python3-pigpio

# Clean up
rm -rf /var/lib/apt/lists/*

pip-3 install -r requirements.txt