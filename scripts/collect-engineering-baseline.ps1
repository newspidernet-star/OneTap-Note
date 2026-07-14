param(
    [ValidateRange(1, 10)]
    [int]$BuildRuns = 3,
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [string]$StartupMetricsPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackendDir = Join-Path $ProjectRoot "backend"
$MetricsRoot = Join-Path $ProjectRoot ".metrics"
$ReportsDir = Join-Path $MetricsRoot "reports"
$RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ReportBase = Join-Path $ReportsDir "engineering-baseline-$RunStamp"
New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null

function Get-Median([double[]]$Values) {
    if (-not $Values -or $Values.Count -eq 0) { return $null }
    $sorted = @($Values | Sort-Object)
    $middle = [math]::Floor($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 1) { return [math]::Round($sorted[$middle], 3) }
    return [math]::Round(($sorted[$middle - 1] + $sorted[$middle]) / 2, 3)
}

function Get-GzipBytes([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $memory = [System.IO.MemoryStream]::new()
    $gzip = [System.IO.Compression.GZipStream]::new(
        $memory,
        [System.IO.Compression.CompressionMode]::Compress,
        $true
    )
    try { $gzip.Write($bytes, 0, $bytes.Length) } finally { $gzip.Dispose() }
    $length = $memory.Length
    $memory.Dispose()
    return [int64]$length
}

function Read-JsonLines([string]$Path) {
    if (-not $Path -or -not (Test-Path $Path)) { return @() }
    $items = @()
    foreach ($line in Get-Content -Path $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $items += ($line | ConvertFrom-Json) } catch {}
    }
    return $items
}

function Invoke-PytestMetric([string]$Name, [string[]]$TestPaths) {
    $tempRoot = Join-Path $MetricsRoot "pytest-temp\$Name-$RunStamp"
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    $arguments = @("-m", "pytest") + $TestPaths + @("-q", "--basetemp", $tempRoot)
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    Push-Location $BackendDir
    try {
        $previousErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $output = @(& ".venv\Scripts\python.exe" @arguments 2>&1 | ForEach-Object { "$_" })
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorPreference
        Pop-Location
        $watch.Stop()
    }
    $logPath = "$ReportBase-$Name-tests.log"
    $output | Set-Content -Path $logPath -Encoding UTF8
    $summary = $output | Where-Object { $_ -match "\d+ (passed|failed|error)" } | Select-Object -Last 1
    return [pscustomobject]@{
        name = $Name
        exit_code = $exitCode
        elapsed_seconds = [math]::Round($watch.Elapsed.TotalSeconds, 3)
        summary = if ($summary) { $summary.Trim() } else { "summary unavailable" }
        log = $logPath.Substring($ProjectRoot.Length + 1).Replace("\", "/")
    }
}

$commit = (git -C $ProjectRoot rev-parse HEAD).Trim()
$shortCommit = (git -C $ProjectRoot rev-parse --short HEAD).Trim()
$commitCount = [int](git -C $ProjectRoot rev-list --count HEAD).Trim()
$trackedFiles = @(git -C $ProjectRoot ls-files)
$coreSourceFiles = @($trackedFiles | Where-Object { $_ -match "^(frontend/src|backend/app)/" }).Count
$frontendSourceFiles = @($trackedFiles | Where-Object { $_ -match "^frontend/src/" }).Count
$backendSourceFiles = @($trackedFiles | Where-Object { $_ -match "^backend/app/" }).Count
$backendTestFiles = @($trackedFiles | Where-Object { $_ -match "^backend/tests/test_.*\.py$" }).Count
$nodeVersion = (& node --version).Trim()
$npmVersion = (& npm.cmd --version).Trim()
$pythonVersion = (& (Join-Path $BackendDir ".venv\Scripts\python.exe") --version 2>&1).Trim()

$buildMetrics = @()
if (-not $SkipBuild) {
    for ($index = 1; $index -le $BuildRuns; $index++) {
        Write-Host "Frontend production build $index/$BuildRuns..." -ForegroundColor Cyan
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        Push-Location $FrontendDir
        try {
            $previousErrorPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $output = @(& npm.cmd run build 2>&1 | ForEach-Object { "$_" })
            $exitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorPreference
            Pop-Location
            $watch.Stop()
        }
        $logPath = "$ReportBase-build-$index.log"
        $output | Set-Content -Path $logPath -Encoding UTF8
        $buildMetrics += [pscustomobject]@{
            run = $index
            exit_code = $exitCode
            elapsed_seconds = [math]::Round($watch.Elapsed.TotalSeconds, 3)
            log = $logPath.Substring($ProjectRoot.Length + 1).Replace("\", "/")
        }
        if ($exitCode -ne 0) { throw "Frontend build $index failed. See $logPath" }
    }
}

$assetFiles = @(Get-ChildItem (Join-Path $FrontendDir "dist\assets") -File -ErrorAction SilentlyContinue)
$jsFiles = @($assetFiles | Where-Object Extension -eq ".js")
$cssFiles = @($assetFiles | Where-Object Extension -eq ".css")
$jsBytes = [int64](($jsFiles | Measure-Object Length -Sum).Sum)
$cssBytes = [int64](($cssFiles | Measure-Object Length -Sum).Sum)
$jsGzipBytes = [int64](($jsFiles | ForEach-Object { Get-GzipBytes $_.FullName } | Measure-Object -Sum).Sum)
$cssGzipBytes = [int64](($cssFiles | ForEach-Object { Get-GzipBytes $_.FullName } | Measure-Object -Sum).Sum)
$largestJs = $jsFiles | Sort-Object Length -Descending | Select-Object -First 1

$tests = @()
if (-not $SkipTests) {
    Write-Host "Running focused ASR reliability tests..." -ForegroundColor Cyan
    $tests += Invoke-PytestMetric "focused-asr" @("tests/test_tunnel.py", "tests/test_speech.py")
    Write-Host "Running full backend test suite..." -ForegroundColor Cyan
    $tests += Invoke-PytestMetric "full-backend" @("tests")
}

$artifacts = @()
$artifactCandidates = @(
    Get-ChildItem (Join-Path $ProjectRoot "desktop\dist-installer") -Filter "*.exe" -File -ErrorAction SilentlyContinue
    Get-ChildItem (Join-Path $ProjectRoot "release") -Filter "*.zip" -File -ErrorAction SilentlyContinue
    Get-Item (Join-Path $ProjectRoot "One Tap Note.exe") -ErrorAction SilentlyContinue
)
foreach ($file in $artifactCandidates) {
    $artifacts += [pscustomobject]@{
        path = $file.FullName.Substring($ProjectRoot.Length + 1).Replace("\", "/")
        bytes = $file.Length
        mib = [math]::Round($file.Length / 1MB, 2)
    }
}

$processingPath = Join-Path $BackendDir "storage\metrics\processing-runs.jsonl"
$processingRuns = @(Read-JsonLines $processingPath)
$stageSamples = @()
$allStages = @($processingRuns | ForEach-Object { $_.completed_stages } | Where-Object { $_ })
foreach ($group in @($allStages | Group-Object stage)) {
    $values = @($group.Group | ForEach-Object { [double]$_.duration_seconds })
    $stageSamples += [pscustomobject]@{
        stage = $group.Name
        samples = $values.Count
        median_seconds = Get-Median $values
        min_seconds = [math]::Round(($values | Measure-Object -Minimum).Minimum, 3)
        max_seconds = [math]::Round(($values | Measure-Object -Maximum).Maximum, 3)
    }
}

if (-not $StartupMetricsPath) {
    $startupCandidates = @(
        (Join-Path $env:APPDATA "One Tap Note\metrics\startup-runs.jsonl"),
        (Join-Path $env:APPDATA "one-tap-note-desktop\metrics\startup-runs.jsonl"),
        (Join-Path $env:APPDATA "one-tap-note\metrics\startup-runs.jsonl")
    )
    $StartupMetricsPath = $startupCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
$startupRuns = if ($StartupMetricsPath) { @(Read-JsonLines $StartupMetricsPath) } else { @() }
$startupSummary = @()
foreach ($group in @($startupRuns | Group-Object mode)) {
    $values = @($group.Group | ForEach-Object { [double]$_.total_startup_ms })
    $startupSummary += [pscustomobject]@{
        mode = $group.Name
        samples = $values.Count
        median_ms = Get-Median $values
        min_ms = [math]::Round(($values | Measure-Object -Minimum).Minimum, 1)
        max_ms = [math]::Round(($values | Measure-Object -Maximum).Maximum, 1)
    }
}

$buildTimes = @($buildMetrics | ForEach-Object { [double]$_.elapsed_seconds })
$report = [ordered]@{
    schema_version = 1
    measured_at = (Get-Date).ToString("o")
    commit = $commit
    environment = [ordered]@{
        os = [System.Environment]::OSVersion.VersionString
        architecture = $env:PROCESSOR_ARCHITECTURE
        node = $nodeVersion
        npm = $npmVersion
        python = $pythonVersion
    }
    repository = [ordered]@{
        commit_count = $commitCount
        tracked_files = $trackedFiles.Count
        core_source_files = $coreSourceFiles
        frontend_source_files = $frontendSourceFiles
        backend_source_files = $backendSourceFiles
        backend_test_files = $backendTestFiles
    }
    frontend_build = [ordered]@{
        runs = $buildMetrics
        median_seconds = Get-Median $buildTimes
        js_files = $jsFiles.Count
        js_bytes = $jsBytes
        js_gzip_bytes = $jsGzipBytes
        css_files = $cssFiles.Count
        css_bytes = $cssBytes
        css_gzip_bytes = $cssGzipBytes
        largest_js_file = if ($largestJs) { $largestJs.Name } else { $null }
        largest_js_bytes = if ($largestJs) { $largestJs.Length } else { 0 }
    }
    tests = $tests
    artifacts = $artifacts
    processing = [ordered]@{
        metrics_path = $processingPath.Substring($ProjectRoot.Length + 1).Replace("\", "/")
        runs = $processingRuns.Count
        stages = $stageSamples
    }
    startup = [ordered]@{
        metrics_path = $StartupMetricsPath
        runs = $startupRuns.Count
        modes = $startupSummary
    }
}

$jsonPath = "$ReportBase.json"
$markdownPath = "$ReportBase.md"
$report | ConvertTo-Json -Depth 12 | Set-Content -Path $jsonPath -Encoding UTF8

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("# One Tap Note engineering baseline")
$lines.Add("")
$lines.Add("- Measured at: $($report.measured_at)")
$lines.Add("- Git commit: ``$shortCommit``")
$lines.Add("- Environment: $nodeVersion / npm $npmVersion / $pythonVersion")
$lines.Add("")
$lines.Add("## Repository scale")
$lines.Add("")
$lines.Add("- Git commits: $commitCount")
$lines.Add("- Core source files: $coreSourceFiles (frontend $frontendSourceFiles, backend $backendSourceFiles)")
$lines.Add("- Backend test files: $backendTestFiles")
$lines.Add("")
$lines.Add("## Frontend build")
$lines.Add("")
$lines.Add("- Repeated builds: $($buildMetrics.Count); median: $($report.frontend_build.median_seconds) s")
$lines.Add("- JavaScript: $([math]::Round($jsBytes / 1KB, 2)) KiB; gzip $([math]::Round($jsGzipBytes / 1KB, 2)) KiB")
$lines.Add("- CSS: $([math]::Round($cssBytes / 1KB, 2)) KiB; gzip $([math]::Round($cssGzipBytes / 1KB, 2)) KiB")
if ($largestJs) { $lines.Add("- Largest JS file: ``$($largestJs.Name)``; $([math]::Round($largestJs.Length / 1KB, 2)) KiB") }
$lines.Add("")
$lines.Add("## Automated tests")
$lines.Add("")
if ($tests.Count -eq 0) { $lines.Add("- Tests skipped for this run.") }
foreach ($test in $tests) { $lines.Add("- $($test.name): $($test.summary); command time $($test.elapsed_seconds) s") }
$lines.Add("")
$lines.Add("## Release artifacts")
$lines.Add("")
if ($artifacts.Count -eq 0) { $lines.Add("- No local release artifacts found.") }
foreach ($artifact in $artifacts) { $lines.Add("- ``$($artifact.path)``: $($artifact.mib) MiB") }
$lines.Add("")
$lines.Add("## Processing samples")
$lines.Add("")
$lines.Add("- Completed runs recorded: $($processingRuns.Count)")
if ($processingRuns.Count -eq 0) { $lines.Add("- Timing collection is installed; run real tasks to build a representative sample.") }
foreach ($stage in $stageSamples) { $lines.Add("- $($stage.stage): n=$($stage.samples), median=$($stage.median_seconds) s, range=$($stage.min_seconds)-$($stage.max_seconds) s") }
$lines.Add("")
$lines.Add("## Desktop startup samples")
$lines.Add("")
$lines.Add("- Startup runs recorded: $($startupRuns.Count)")
if ($startupRuns.Count -eq 0) { $lines.Add("- Timing collection is installed; launch the desktop app normally to collect cold and warm samples.") }
foreach ($mode in $startupSummary) { $lines.Add("- $($mode.mode): n=$($mode.samples), median=$($mode.median_ms) ms, range=$($mode.min_ms)-$($mode.max_ms) ms") }
$lines.Add("")
$lines.Add("Raw command output and JSON are stored beside this report under the ignored ``.metrics`` directory.")
$lines | Set-Content -Path $markdownPath -Encoding UTF8

Write-Host "Baseline JSON: $jsonPath" -ForegroundColor Green
Write-Host "Baseline Markdown: $markdownPath" -ForegroundColor Green
