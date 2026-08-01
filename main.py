from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from email_processor import process_emails

scheduler = BlockingScheduler()

def run_job():
    current_time = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
    print("=" * 60)
    print(f"RFQ Email Processing Started")
    print(f"Execution Time: {current_time}")
    print("=" * 60)

    process_emails()

    print(f"Completed at: {datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')}")
    print("=" * 60)
    print()

# Run immediately when the application starts
run_job()

# Run every 5 minutes
scheduler.add_job(
    run_job,
    trigger="interval",
    minutes=5,
    id="rfq_email_job",
    replace_existing=True
)

print("RFQ Email Scheduler Started...")
print("Checking emails every 5 minutes...")
print(f"Scheduler Started At: {datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')}")

scheduler.start()