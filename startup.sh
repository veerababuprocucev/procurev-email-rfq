#!/bin/bash
echo "Starting ProcureV RFQ Email Service with Gunicorn..."
gunicorn --bind=0.0.0.0:${PORT:-8000} --timeout 600 main:app
