$user = "`$procurev-rfq-cron"
$pass = "xvGzvrcyqioyRX9qa7yTtR2B2oPBTD0qXrA31CccH67gbHxarhLREeJ6025k"
$pair = "${user}:${pass}"
$bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
$base64 = [Convert]::ToBase64String($bytes)
$headers = @{ Authorization = "Basic $base64" }

Write-Host "Publishing deploy.zip to Azure ZipDeploy REST API..."
$response = Invoke-RestMethod -Uri "https://procurev-rfq-cron.scm.azurewebsites.net/api/zipdeploy" -Method Post -InFile "deploy.zip" -ContentType "application/octet-stream" -Headers $headers
Write-Host "Deployment Response:" $response
