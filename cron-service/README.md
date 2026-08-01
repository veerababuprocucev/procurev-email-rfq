# ProcureV RFQ Node.js Cron Service

This is a standalone Node.js cron scheduler service located in `cron-service/` that triggers the Python RFQ email processing job.

## Setup

```bash
cd cron-service
npm install
```

## Running the Cron Service

### 1. Continuous Cron Mode (Every 5 Minutes)
```bash
npm start
```
*or*
```bash
node index.js
```

### 2. Single Run (One-time trigger)
```bash
npm run once
```
*or*
```bash
node index.js --once
```

## Configuration

You can customize the schedule or Python executable using environment variables:

```bash
# Run every 10 minutes
CRON_SCHEDULE="*/10 * * * *" node index.js
```
