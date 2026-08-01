import azure.functions as func
import logging
import datetime
from email_processor import process_emails

app = func.FunctionApp()

# Azure Timer Trigger Cron Format: "second minute hour day month day-of-week"
# "0 */5 * * * *" = Trigger every 5 minutes
@app.timer_trigger(
    schedule="0 */5 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def rfq_email_processing_cron(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    if myTimer.past_due:
        logging.info("Azure Timer job is past due!")

    logging.info(f"========== Azure Cron Job Started: {utc_timestamp} ==========")
    
    try:
        process_emails()
        logging.info("========== Azure Cron Job Completed Successfully ==========")
    except Exception as e:
        logging.error(f"Error during RFQ Email Processing in Azure: {str(e)}")
