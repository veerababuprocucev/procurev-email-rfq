# Azure Deployment Guide for ProcureV RFQ Cron Job

This project contains production-ready Azure Functions V2 code to run your RFQ email processing as an automatic serverless cron job on **Microsoft Azure**.

---

## Azure Files Created

- **[function_app.py](file:///c:/Users/Procucev/AI/procurev-email-rfq-main/function_app.py)**: Azure Functions Timer Trigger entrypoint (`schedule="0 */5 * * * *"` = every 5 minutes).
- **[host.json](file:///c:/Users/Procucev/AI/procurev-email-rfq-main/host.json)**: Azure Function host configuration.
- **[local.settings.json](file:///c:/Users/Procucev/AI/procurev-email-rfq-main/local.settings.json)**: Local development environment settings.
- **[Dockerfile](file:///c:/Users/Procucev/AI/procurev-email-rfq-main/Dockerfile)**: Docker container configuration for Azure Container Apps / Web Apps for Containers.

---

## Deployment Option A: Deploy via Azure Functions Core Tools (CLI - Recommended)

### Prerequisites
Install Azure CLI and Azure Functions Core Tools:
```bash
npm install -g azure-functions-core-tools@4 --unsafe-perm true
az login
```

### Steps to Deploy

1. **Create Resource Group**:
   ```bash
   az group create --name procurev-rfq-rg --location eastus
   ```

2. **Create Storage Account**:
   ```bash
   az storage account create --name procurevrfqsa --location eastus --resource-group procurev-rfq-rg --sku Standard_LRS
   ```

3. **Create Function App (Python 3.11)**:
   ```bash
   az functionapp create --resource-group procurev-rfq-rg --consumption-plan-location eastus --runtime python --runtime-version 3.11 --functions-version 4 --name procurev-rfq-cron --storage-account procurevrfqsa --os-type linux
   ```

4. **Publish Code to Azure**:
   ```bash
   func azure functionapp publish procurev-rfq-cron
   ```

---

## Deployment Option B: Deploy via Docker / Azure Container Apps

1. **Build and push Docker Image**:
   ```bash
   docker build -t procurevrfq.azurecr.io/rfq-cron:v1 .
   docker push procurevrfq.azurecr.io/rfq-cron:v1
   ```

2. **Deploy to Azure Container App / App Service**:
   Configure container to run continuously on Azure.
