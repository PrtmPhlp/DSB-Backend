"""Scheduler module for running periodic tasks using the schedule library."""

import asyncio
import multiprocessing
import signal
import socket
import sys
import time

import schedule
from waitress import serve

import app
import runner


def task():
    """Execute the main runner script and log its execution."""
    print("Executing the script...")
    try:
        runner.main()
    except Exception as e:
        print(f"ERROR: {e}")


def signal_handler(*_):
    """Handle shutdown gracefully on SIGINT/SIGTERM."""
    print("Shutting down scheduler...")
    sys.exit(0)


def run_flask_app():
    """Run the Flask application."""
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"PRODUCTION: Server running on http://{local_ip}:5555")
    serve(app.app, host='0.0.0.0', port=5555)


def main():
    """Initialize and run the scheduler."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start Flask app in a separate process
    flask_process = multiprocessing.Process(target=run_flask_app)
    flask_process.start()

    # Execute immediately upon startup
    task()

    # Schedule the task to run every 30 seconds
    # schedule.every(30).seconds.do(task)
    schedule.every(5).minutes.do(task)

    # Run the scheduled tasks indefinitely
    try:
        while True:
            schedule.run_pending()
            time.sleep(5)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print("Error in scheduler: %s", e)
        flask_process.terminate()
        sys.exit(1)
    finally:
        flask_process.terminate()


if __name__ == '__main__':
    main()
