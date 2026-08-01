/**
 * Node.js Cron Job Service for ProcureV RFQ Email Processing
 * Spawns the Python RFQ processor on a cron schedule (default: every 5 minutes).
 */

const cron = require('node-cron');
const { spawn } = require('child_process');
const path = require('path');

// Configuration
const CRON_SCHEDULE = process.env.CRON_SCHEDULE || '*/5 * * * *'; // Default: Every 5 minutes
const PYTHON_PATH = process.env.PYTHON_PATH || 'python';
const PROJECT_DIR = path.resolve(__dirname, '..');
const SCRIPT_PATH = path.join(PROJECT_DIR, 'cron_job.py');

/**
 * Executes the Python RFQ email processing script
 */
function runPythonJob() {
    return new Promise((resolve, reject) => {
        const timestamp = new Date().toLocaleString();
        console.log('='.repeat(60));
        console.log(`[NODE CRON] Executing RFQ Processing Job`);
        console.log(`[NODE CRON] Start Time: ${timestamp}`);
        console.log(`[NODE CRON] Python Script: ${SCRIPT_PATH}`);
        console.log('='.repeat(60));

        // Spawn python process
        const pythonProcess = spawn(PYTHON_PATH, [SCRIPT_PATH, '--once'], {
            cwd: PROJECT_DIR
        });

        pythonProcess.stdout.on('data', (data) => {
            process.stdout.write(data.toString());
        });

        pythonProcess.stderr.on('data', (data) => {
            process.stderr.write(data.toString());
        });

        pythonProcess.on('error', (err) => {
            console.error(`[NODE CRON ERROR] Failed to start Python process: ${err.message}`);
            reject(err);
        });

        pythonProcess.on('close', (code) => {
            const endTimestamp = new Date().toLocaleString();
            console.log('='.repeat(60));
            if (code === 0) {
                console.log(`[NODE CRON] Job completed successfully at ${endTimestamp}`);
                resolve();
            } else {
                console.error(`[NODE CRON] Job failed with exit code ${code} at ${endTimestamp}`);
                reject(new Error(`Exit code ${code}`));
            }
            console.log('='.repeat(60) + '\n');
        });
    });
}

// Check command line flags
const isOnce = process.argv.includes('--once');

if (isOnce) {
    console.log('[NODE CRON] Single-run mode active (--once)...');
    runPythonJob().catch((err) => {
        process.exit(1);
    });
} else {
    console.log('='.repeat(60));
    console.log(' ProcureV RFQ Node.js Cron Service Started');
    console.log(` Schedule:        ${CRON_SCHEDULE} (Every 5 minutes)`);
    console.log(` Project Path:    ${PROJECT_DIR}`);
    console.log(' Press Ctrl+C to stop.');
    console.log('='.repeat(60) + '\n');

    // Run initial execution immediately
    console.log('[NODE CRON] Running initial execution immediately...');
    runPythonJob().catch(() => {});

    // Schedule the cron task
    cron.schedule(CRON_SCHEDULE, () => {
        runPythonJob().catch((err) => {
            console.error(`[NODE CRON] Scheduled run encountered an error:`, err.message);
        });
    });
}
