# PowerShell test script for /v1/forecasts/yearly/forecast endpoint

Write-Host "Testing /v1/forecasts/yearly/forecast endpoint..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Check if server is running
try {
    $healthCheck = Invoke-WebRequest -Uri "http://localhost:8081/docs" -Method GET -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Server is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Server is not running on port 8081" -ForegroundColor Red
    Write-Host "Start it with: python -m uvicorn api.app:app --reload --port 8081" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Sending request (this may take 30-60 seconds for LLM processing)..." -ForegroundColor Yellow
Write-Host ""

# Read the test payload
$jsonContent = Get-Content -Path "test_yearly_forecast_story.json" -Raw

# Make the request
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8081/v1/forecasts/yearly/forecast" `
        -Method POST `
        -ContentType "application/json" `
        -Body $jsonContent `
        -TimeoutSec 120 `
        -UseBasicParsing

    $stopwatch.Stop()
    $elapsed = $stopwatch.Elapsed.TotalSeconds

    # Save response
    $response.Content | Out-File -FilePath "response_yearly_story.json" -Encoding UTF8

    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "✅ Request successful!" -ForegroundColor Green
    Write-Host "HTTP Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Total Time: $([math]::Round($elapsed, 2))s" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response saved to: response_yearly_story.json" -ForegroundColor White
    Write-Host ""
    
    # Parse response and show structure
    $jsonResponse = $response.Content | ConvertFrom-Json
    
    Write-Host "Response structure:" -ForegroundColor White
    Write-Host "  - report.meta (year: $($jsonResponse.report.meta.year))" -ForegroundColor Gray
    Write-Host "  - report.year_at_glance (top_events: $($jsonResponse.report.year_at_glance.top_events.Count))" -ForegroundColor Gray
    Write-Host "  - report.eclipses_and_lunations ($($jsonResponse.report.eclipses_and_lunations.Count) events)" -ForegroundColor Gray
    Write-Host "  - report.months ($($jsonResponse.report.months.Count) sections)" -ForegroundColor Gray
    Write-Host "  - report.appendix_all_events ($($jsonResponse.report.appendix_all_events.Count) events)" -ForegroundColor Gray
    Write-Host "  - pdf_download_url: $($jsonResponse.pdf_download_url)" -ForegroundColor Gray
    Write-Host ""
    
    if ($jsonResponse.pdf_download_url) {
        Write-Host "📄 PDF available at: $($jsonResponse.pdf_download_url)" -ForegroundColor Cyan
    }

} catch {
    $stopwatch.Stop()
    $elapsed = $stopwatch.Elapsed.TotalSeconds
    
    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "❌ Request failed!" -ForegroundColor Red
    Write-Host "HTTP Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Total Time: $([math]::Round($elapsed, 2))s" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try to get error details
    try {
        $errorStream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorStream)
        $errorContent = $reader.ReadToEnd()
        $reader.Close()
        
        Write-Host ""
        Write-Host "Error details:" -ForegroundColor Yellow
        Write-Host $errorContent -ForegroundColor Yellow
    } catch {
        # Ignore if we can't read error details
    }
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "To view the full response:" -ForegroundColor White
Write-Host "  Get-Content response_yearly_story.json | ConvertFrom-Json | ConvertTo-Json -Depth 10 | more" -ForegroundColor Gray

