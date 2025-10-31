# ==========================
# Chaos Simulation Script
# ==========================

$baseNginx = "http://localhost:8080/version"
$chaosOn = "http://localhost:8081/chaos/start?mode=error"
$chaosOff = "http://localhost:8081/chaos/stop"
$totalRequests = 120
$toggleInterval = 3  # Toggle error every 20 requests
$inErrorMode = $false

Write-Host "🚀 Starting Chaos Simulation..."
Write-Host "Sending $totalRequests requests to $baseNginx with chaos toggled every $toggleInterval requests"
Write-Host ""

for ($i = 1; $i -le $totalRequests; $i++) {
    # Toggle error mode every N requests
    if ($i % $toggleInterval -eq 0) {
        if ($inErrorMode) {
            Write-Host "`n[$i] 🟢 Turning OFF error mode on Blue..."
            try {
                Invoke-WebRequest -Uri $chaosOff -Method POST -UseBasicParsing | Out-Null
                $inErrorMode = $false
            } catch {
                Write-Host "Failed to stop chaos: $($_.Exception.Message)"
            }
        } else {
            Write-Host "`n[$i] 🔴 Turning ON error mode on Blue..."
            try {
                Invoke-WebRequest -Uri $chaosOn -Method POST -UseBasicParsing | Out-Null
                $inErrorMode = $true
            } catch {
                Write-Host "Failed to start chaos: $($_.Exception.Message)"
            }
        }
    }

    # Send request to Nginx (load balancer)
    try {
        $response = Invoke-WebRequest -Uri $baseNginx -Method GET -UseBasicParsing
        Write-Host "[$i] ✅ Status: $($response.StatusCode)"
    } catch {
        Write-Host "[$i] ❌ Error: $($_.Exception.Response.StatusCode.value__)"
    }

    Start-Sleep -Milliseconds 100
}

# Ensure chaos is turned off at the end
Write-Host "`n🧹 Stopping any remaining chaos mode..."
try {
    Invoke-WebRequest -Uri $chaosOff -Method POST -UseBasicParsing | Out-Null
} catch {
    Write-Host "Cleanup failed: $($_.Exception.Message)"
}

Write-Host "`n✅ Simulation complete!"
