"""
ProcureV RFQ Email Processing Application
Flask WSGI Web Application + APScheduler Background Cron Daemon for Azure App Service
"""

import threading
import os
from flask import Flask, jsonify
from cron_job import start_cron_scheduler, execute_rfq_job

app = Flask(__name__)

# Start 5-minute background cron scheduler thread when Gunicorn/Python imports main.py
def _start_background_cron():
    print("Starting 5-minute background RFQ Email Processing scheduler...")
    start_cron_scheduler(cron_expression="*/5 * * * *", run_immediately=True)

cron_thread = threading.Thread(target=_start_background_cron, daemon=True)
cron_thread.start()


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "SUCCESS",
        "service": "ProcureV RFQ Email Processing Service",
        "mode": "Background Cron Daemon Active (Every 5 Minutes)",
        "message": "App Service is running 24/7"
    }), 200


@app.route("/api/run_rfq_job", methods=["GET", "POST"])
def trigger_rfq_job():
    try:
        execute_rfq_job()
        return jsonify({
            "status": "SUCCESS",
            "message": "RFQ Email Processing Executed Successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)