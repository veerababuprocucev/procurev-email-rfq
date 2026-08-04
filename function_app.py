import azure.functions as func
import logging
import datetime
import json
from cron_job import execute_rfq_job

app = func.FunctionApp()

@app.function_name(name="rfq_email_processing_cron")
@app.timer_trigger(
    schedule="0 */5 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def rfq_email_processing_cron(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if myTimer.past_due:
        logging.info("Azure Timer job execution is past due.")

    logging.info(f"========== Azure Function Cron Execution Started: {utc_timestamp} ==========")
    execute_rfq_job()
    logging.info("========== Azure Function Cron Execution Completed ==========")


@app.function_name(name="run_rfq_job_http")
@app.route(route="run_rfq_job", auth_level=func.AuthLevel.ANONYMOUS)
def run_rfq_job_http(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP Trigger endpoint to manually run the RFQ processing job via URL."""
    logging.info("HTTP trigger received for manual RFQ processing.")
    try:
        execute_rfq_job()
        return func.HttpResponse(
            json.dumps({"status": "SUCCESS", "message": "RFQ Email Processing Completed Successfully"}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"status": "ERROR", "error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
