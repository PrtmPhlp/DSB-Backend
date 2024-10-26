import schedule
import time


def task():
    print("Executing the script...")


# Execute immediately upon startup
task()

# Schedule the task to run every 5 minutes
schedule.every(30).seconds.do(task)

# Run the scheduled tasks indefinitely
while True:
    schedule.run_pending()
    time.sleep(1)
