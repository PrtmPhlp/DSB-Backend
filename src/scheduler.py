#!/usr/bin/env python3
# -----------------------------------------------------------
"""
Scheduler module for running periodic tasks using the schedule library.
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
from teacher_scraper import TeacherScraper


from logger_setup import LoggerSetup

# ---------------------------------------------------------------------------
# 1) Logger Setup
# ---------------------------------------------------------------------------
logger = LoggerSetup.setup_logger("Scheduler")

# Global flag for shutdown
SHOULD_EXIT = False


def task() -> None:
    """
    Execute the main runner script and log its execution.
    First update teacher data, then run the main DSB scraper.
    """
    logger.info("Starting scheduled task execution...")
    try:
        # First update teacher data
        teacher_scraper = TeacherScraper(
            url='https://www.goerres-koblenz.de/kollegium/',
            output_path='schema/lehrer.json'
        )
        teacher_scraper.run()

        # Then run main DSB scraping task
        runner.main(scheduled_mode=True)
        logger.info("Task completed successfully")
    except Exception as e:
        logger.error("Error during task execution: %s", e, exc_info=True)


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
            logger.info("Starting Flask server on http://%s:5555", local_ip)
            serve(flask_app, host='0.0.0.0', port=5555)
        except Exception as e:
            logger.error("Flask server crashed: %s", e, exc_info=True)
            logger.info("Restarting Flask server in 5 seconds...")
            time.sleep(5)


def signal_handler(signum: int, _) -> None:
    """
    Handle shutdown gracefully on SIGINT/SIGTERM.
    """
    global SHOULD_EXIT  # pylint: disable=global-statement
    logger.info("Received signal %s, initiating shutdown...", signum)
    SHOULD_EXIT = True


def main() -> None:
    """
    Initialize and run the scheduler with improved error handling and automatic restarts.
    """
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
        while not SHOULD_EXIT:
            schedule.run_pending()
            time.sleep(1)
    except Exception as e:
        logger.error("Error in scheduler loop: %s", e, exc_info=True)
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
