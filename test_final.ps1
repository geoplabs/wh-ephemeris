$dates = @("2025-10-29", "2025-11-10", "2025-11-15")

Write-Host "`n===== NETTING STRATEGY TEST =====" -ForegroundColor Cyan

foreach ($d in $dates) {
    $body = @"
{
  "chart_input": {
    "system": "western",
    "date": "1995-07-10",
    "time": "12:00:00",
    "time_known": true,
    "place": {"lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles"}
  },
  "options": {
    "date": "$d",
    "profile_name": "Test",
    "use_ai": false
  }
}
"@
    
    $r = Invoke-RestMethod -Uri http://localhost:8081/v1/forecasts/daily/forecast -Method Post -Body $body -ContentType "application/json"
    
    Write-Host "`n$d" -ForegroundColor White
    Write-Host "  Caution: $($r.caution_window.time_window)" -ForegroundColor Red
    Write-Host "  Lucky:   $($r.lucky.time_window)" -ForegroundColor Green
    
    if ($r.caution_window.time_window -eq $r.lucky.time_window) {
        Write-Host "  ⚠️  IDENTICAL WINDOWS!" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Different windows" -ForegroundColor DarkGreen
    }
}

Write-Host "`n"

