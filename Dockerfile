# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

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
ENV PYTHONUNBUFFERED=1
ENV DSB_USERNAME=""
ENV DSB_PASSWORD=""

# Run the scheduler script
CMD ["python", "src/scheduler.py"]
