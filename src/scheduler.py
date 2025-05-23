#!/usr/bin/env python3
# -----------------------------------------------------------
"""
Scheduler module for running periodic tasks using the schedule library.

It:
- Runs the Flask server (from server.py) in a separate process with auto-restart
- Executes runner.main() every 2 minutes
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

# Logging from external file
from logger_setup import LoggerSetup

# ---------------------------------------------------------------------------
# 1) Logger Setup
# ---------------------------------------------------------------------------
logger = LoggerSetup.setup_logger("Scheduler")
# Global flag for shutdown
should_exit = False


def task() -> None:
    """
    Execute the main runner script and log its execution.
    """
    logger.info("Starting scheduled task execution...")
    try:
        runner.main(scheduled_mode=True)
        logger.info("Task completed successfully")
    except Exception as e:
        logger.error(f"Error during task execution: {e}", exc_info=True)


def run_flask_app(exit_event) -> None:
    """
    Create and run the Flask application in production mode with Waitress.
    Will automatically restart on crashes.
    """
    while not exit_event.is_set():
        try:
            flask_app = create_app()
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            logger.info(f"Starting Flask server on http://{local_ip}:5555")
            serve(flask_app, host='0.0.0.0', port=5555)
        except Exception as e:
            logger.error(f"Flask server crashed: {e}", exc_info=True)
            logger.info("Restarting Flask server in 5 seconds...")
            time.sleep(5)


def signal_handler(signum: int, _) -> None:
    """
    Handle shutdown gracefully on SIGINT/SIGTERM.
    """
    global should_exit
    logger.info(f"Received signal {signum}, initiating shutdown...")
    should_exit = True


def main() -> None:
    """
    Initialize and run the scheduler with improved error handling and automatic restarts.
    """
    global should_exit

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create an event for signaling the Flask process to shut down
    flask_exit = multiprocessing.Event()

    # Start Flask app in a separate process with auto-restart capability
    flask_process = multiprocessing.Process(
        target=run_flask_app,
        args=(flask_exit,),
        daemon=True
    )
    flask_process.start()
    logger.info("Flask process started")

    # Execute task immediately upon startup
    task()

    # Schedule the task to run every 2 minutes
    schedule.every(2).minutes.do(task)
    logger.info("Scheduled task to run every 2 minutes")

    try:
        while not should_exit:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error in scheduler loop: {e}", exc_info=True)
    finally:
        logger.info("Shutting down...")
        flask_exit.set()  # Signal Flask process to exit
        flask_process.join(timeout=5)  # Wait for Flask process to finish
        if flask_process.is_alive():
            flask_process.terminate()
            logger.info("Flask process terminated")
        sys.exit(0)


if __name__ == '__main__':
    main()
