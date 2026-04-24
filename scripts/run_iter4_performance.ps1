param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Token = "",
    [int]$PublicSamples = 300,
    [int]$PublicConcurrency = 20,
    [int]$TradeSamples = 200,
    [int]$TradeConcurrency = 20,
    [int]$ProductId = 1,
    [string]$OrderId = "",
    [int]$OrderItemId = 0,
    [string]$OutputDir = "docs/testing/iter4/results"
)

$ErrorActionPreference = "Stop"

function Invoke-Once {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [string]$Body
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        if ($Body) {
            Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers -Body $Body -ContentType "application/json" -UseBasicParsing | Out-Null
        } else {
            Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers -UseBasicParsing | Out-Null
        }
        $ok = $true
    } catch {
        $ok = $false
    }
    $sw.Stop()
    [pscustomobject]@{ ok = $ok; ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 2) }
}

function Get-Percentile {
    param([double[]]$Values, [double]$Percentile)
    if (-not $Values -or $Values.Count -eq 0) { return 0 }
    $sorted = $Values | Sort-Object
    $idx = [math]::Ceiling(($Percentile / 100) * $sorted.Count) - 1
    $idx = [math]::Max(0, [math]::Min($idx, $sorted.Count - 1))
    return [math]::Round($sorted[$idx], 2)
}

function Invoke-Benchmark {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Path,
        [int]$Samples,
        [int]$Concurrency,
        [hashtable]$Headers,
        [string]$Body = ""
    )

    Write-Host "Running ${Name}: $Samples samples / $Concurrency concurrency"
    $url = "$BaseUrl$Path"
    $results = New-Object System.Collections.Generic.List[object]
    $remaining = $Samples

    while ($remaining -gt 0) {
        $batch = [math]::Min($Concurrency, $remaining)
        $jobs = @()
        for ($i = 0; $i -lt $batch; $i++) {
            $jobs += Start-Job -ScriptBlock ${function:Invoke-Once} -ArgumentList $Method, $url, $Headers, $Body
        }
        $batchResults = $jobs | Receive-Job -Wait
        $jobs | Remove-Job
        foreach ($item in $batchResults) { $results.Add($item) }
        $remaining -= $batch
    }

    $success = @($results | Where-Object { $_.ok })
    $latencies = @($success | ForEach-Object { [double]$_.ms })
    [pscustomobject]@{
        name = $Name
        samples = $Samples
        concurrency = $Concurrency
        success = $success.Count
        failed = $Samples - $success.Count
        success_rate = if ($Samples -gt 0) { [math]::Round($success.Count / $Samples, 4) } else { 0 }
        p50_ms = Get-Percentile $latencies 50
        p95_ms = Get-Percentile $latencies 95
        p99_ms = Get-Percentile $latencies 99
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$headers = @{}
if ($Token) { $headers["Authorization"] = "Bearer $Token" }

$report = New-Object System.Collections.Generic.List[object]
$report.Add((Invoke-Benchmark -Name "top-sales" -Method "GET" -Path "/api/products/products/top-sales/?limit=10" -Samples $PublicSamples -Concurrency $PublicConcurrency -Headers $headers))
$report.Add((Invoke-Benchmark -Name "hot-feed" -Method "GET" -Path "/api/products/products/hot-feed/?limit=10" -Samples $PublicSamples -Concurrency $PublicConcurrency -Headers $headers))

if ($Token) {
    $priceBody = @{ items = @(@{ product_id = $ProductId; quantity = 1 }) } | ConvertTo-Json -Depth 5
    $report.Add((Invoke-Benchmark -Name "price-preview" -Method "POST" -Path "/api/orders/orders/price-preview/" -Samples $PublicSamples -Concurrency $PublicConcurrency -Headers $headers -Body $priceBody))

    if ($OrderId -and $OrderItemId -gt 0) {
        $idem = [guid]::NewGuid().ToString("N")
        $refundBody = @{ order_id = $OrderId; order_item_id = $OrderItemId; quantity = 1; reason = "iter4-perf"; idempotency_key = $idem } | ConvertTo-Json -Depth 5
        $report.Add((Invoke-Benchmark -Name "refund-create" -Method "POST" -Path "/api/refunds/" -Samples $TradeSamples -Concurrency $TradeConcurrency -Headers $headers -Body $refundBody))
        $report.Add((Invoke-Benchmark -Name "logistics-query" -Method "GET" -Path "/api/orders/orders/$OrderId/logistics/" -Samples $PublicSamples -Concurrency $PublicConcurrency -Headers $headers))
    }
} else {
    Write-Host "Token not provided. Protected trade benchmarks skipped."
}

$file = Join-Path $OutputDir ("iter4-performance-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json")
$report | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $file
Write-Host "Report written to $file"
