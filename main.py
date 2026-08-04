"""
ProcureV RFQ Email Processing Application Entrypoint for Azure App Service
"""

import threading
from cron_job import start_cron_scheduler, run_http_server

if __name__ == "__main__":
    # Start HTTP server on PORT 8000 in background thread for Azure App Service health check & URL trigger
    web_thread = threading.Thread(target=run_http_server, daemon=True)
    web_thread.start()

    # Start 5-minute APScheduler daemon
    start_cron_scheduler(cron_expression="*/5 * * * *", run_immediately=True)