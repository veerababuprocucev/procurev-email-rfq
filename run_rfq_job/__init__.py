import azure.functions as func
import logging
import json
import os
import sys

# Ensure parent directory is in sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cron_job import execute_rfq_job

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('HTTP trigger processed a request for RFQ processing.')
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
