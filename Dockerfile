# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Combine apt-get commands into one layer, use no-install-recommends, and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl cron && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code directories
COPY src/ ./src/
COPY schema/ ./schema/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DSB_USERNAME="" \
    DSB_PASSWORD=""

# Copy the entrypoint script and ensure it’s executable
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:5555/healthcheck || exit 1

# Set the entrypoint and default command
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "src/scheduler.py"]
