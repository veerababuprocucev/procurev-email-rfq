import azure.functions as func
import logging
import datetime
import os
import sys

# Ensure parent directory is in sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cron_job import execute_rfq_job

def main(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logging.info(f"========== Azure Cron Trigger Executed: {utc_timestamp} ==========")
    execute_rfq_job()
