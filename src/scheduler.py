#!/usr/bin/env python3
# -----------------------------------------------------------
"""
Scheduler module for running periodic tasks using the schedule library.

It:
- Spawns the Flask server (from server.py) in a separate process
- Executes runner.main() on a schedule
- Handles graceful shutdown on SIGINT/SIGTERM
"""

import multiprocessing
import signal
import socket
import sys
import time

import schedule
from waitress import serve

# Import the runner script that does the scraping/task
import main as runner
# Import the server's create_app() function
from app import create_app


def task():
    """
    Execute the main runner script and log its execution.
    You can replace the print statements with actual logging if desired.
    """
    print("Executing the script...")
    try:
        runner.main()
    except Exception as e:
        print(f"ERROR: {e}")


def signal_handler(*_):
    """
    Handle shutdown gracefully on SIGINT/SIGTERM.
    """
    print("Shutting down scheduler...")
    sys.exit(0)


def run_flask_app():
    """
    Create and run the Flask application in production mode with Waitress.
    """
    flask_app = create_app()  # create the Flask application
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"PRODUCTION: Server running on http://{local_ip}:5555")
    serve(flask_app, host='0.0.0.0', port=5555)


def main():
    """
    Initialize and run the scheduler.
    - Start the Flask app in a separate process
    - Schedule periodic tasks
    """
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start Flask app in a separate process
    flask_process = multiprocessing.Process(target=run_flask_app)
    flask_process.start()

    # Execute immediately upon startup
    task()

    # Example: Schedule the task to run every 5 minutes
    schedule.every(5).minutes.do(task)

    # Run the scheduled tasks indefinitely
    try:
        while True:
            schedule.run_pending()
            time.sleep(5)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error in scheduler: {e}")
        flask_process.terminate()
        sys.exit(1)
    finally:
        flask_process.terminate()


if __name__ == '__main__':
    main()
