# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install curl and cron for healthcheck and scheduling
RUN apt-get update && apt-get install -y curl cron && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire source code
COPY src/ ./src/
# COPY json/ ./json/
COPY schema/ ./schema/

# Create necessary directories and files
RUN mkdir -p json && touch json/scraped.json json/formatted.json

# Set environment variables
# ENV PYTHONUNBUFFERED=1
ENV DSB_USERNAME=""
ENV DSB_PASSWORD=""

# Run the scheduler script and cron
CMD cron && python src/scheduler.py
