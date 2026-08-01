"""
Single-file Cron Job Scheduler for ProcureV RFQ Email Processing Project.

Usage Modes:
  1. Daemon Mode (Cron Scheduler):
     python cron_job.py
     Runs continuously and executes email processing based on a cron schedule (default: every 5 minutes).

  2. Custom Cron Schedule:
     python cron_job.py --cron "*/10 * * * *"
     python cron_job.py --cron "0 * * * *"

  3. Single Run (For OS Crontab / Windows Task Scheduler):
     python cron_job.py --once
"""

import sys
import os
import argparse
import signal
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from email_processor import process_emails


def execute_rfq_job():
    """Executes a single run of the RFQ Email Processing job with error isolation."""
    start_time = datetime.now()
    print("=" * 60)
    print("RFQ Email Processing Cron Job Started")
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        process_emails()
        print("\nJob Status: SUCCESS")
    except Exception as e:
        print(f"\nJob Status: ERROR - {str(e)}", file=sys.stderr)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"End Time:   {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Duration: {duration:.2f}s)")
    print("=" * 60 + "\n")


def start_cron_scheduler(cron_expression="*/5 * * * *", run_immediately=True):
    """Starts the blocking cron scheduler daemon."""
    scheduler = BlockingScheduler()

    # Prevent overlapping job runs if execution takes longer than cron interval
    trigger = CronTrigger.from_crontab(cron_expression)

    scheduler.add_job(
        execute_rfq_job,
        trigger=trigger,
        id="rfq_email_cron_job",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    # Handle graceful exit signals (Ctrl+C / kill)
    def shutdown_handler(signum, frame):
        print("\nShutdown signal received. Stopping RFQ Cron Scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_handler)

    print("=" * 60)
    print("ProcureV RFQ Email Cron Scheduler Started")
    print(f"Cron Expression: '{cron_expression}'")
    print(f"Scheduler Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to stop.")
    print("=" * 60 + "\n")

    # Run initial execution immediately if requested
    if run_immediately:
        print("Running initial execution immediately...")
        execute_rfq_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Cron Scheduler stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RFQ Email Processing Cron Job Runner")
    parser.add_argument(
        "--cron",
        type=str,
        default="*/5 * * * *",
        help="Cron expression for scheduling (default: '*/5 * * * *' = every 5 minutes)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the job exactly once and exit (ideal for Linux crontab / Windows Task Scheduler)",
    )
    parser.add_argument(
        "--no-immediate",
        action="store_true",
        help="Do not run immediately on daemon start; wait for the first scheduled trigger",
    )

    args = parser.parse_args()

    if args.once:
        print("Executing single-run mode (--once)...")
        execute_rfq_job()
    else:
        start_cron_scheduler(
            cron_expression=args.cron,
            run_immediately=not args.no_immediate,
        )
