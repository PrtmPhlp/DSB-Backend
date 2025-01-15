# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install curl, cron, and logrotate for healthcheck, scheduling, and log management
RUN apt-get update && apt-get install -y curl cron logrotate && rm -rf /var/lib/apt/lists/*

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

# Add logrotate configuration for your application
RUN echo "/var/log/myapp/*.log {\n    size 5M\n    rotate 5\n    compress\n    missingok\n    notifempty\n}" > /etc/logrotate.d/myapp

# Add cron job to run logrotate daily
RUN echo "0 0 * * * /usr/sbin/logrotate /etc/logrotate.d/myapp" >> /etc/crontab

# Set environment variables
# ENV PYTHONUNBUFFERED=1
ENV DSB_USERNAME=""
ENV DSB_PASSWORD=""

# Run the scheduler script and cron
CMD cron && python src/scheduler.py
