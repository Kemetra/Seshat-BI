$ErrorActionPreference = "Stop"

if ($env:SESHAT_VERSION -notmatch '^\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]+)?$') {
    throw "seshat-version must be an exact immutable version"
}
if ($env:SESHAT_SARIF -notin @("auto", "true", "false")) {
    throw "sarif must be auto, true, or false"
}

$repo = Resolve-Path -LiteralPath $env:SESHAT_REPO
$outputRoot = Join-Path $repo ".seshat-output\review"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

python -m pip install --disable-pip-version-check "seshat-bi==$($env:SESHAT_VERSION)"
if ($LASTEXITCODE -ne 0) { throw "failed to install the pinned seshat-bi version" }

$reviewFile = Join-Path $outputRoot "seshat-review.json"
$arguments = @("check", "--repo", $repo, "--format", "review")
if ($env:SESHAT_COMMIT_RANGE) { $arguments += @("--commit-range", $env:SESHAT_COMMIT_RANGE) }
& seshat @arguments | Set-Content -LiteralPath $reviewFile -Encoding utf8
$reviewExit = $LASTEXITCODE

try {
    $review = Get-Content -LiteralPath $reviewFile -Raw | ConvertFrom-Json
} catch {
    throw "Seshat review output was not valid JSON"
}

$summary = @(
    "## Seshat BI review: $($review.outcome.ToString().ToUpperInvariant())",
    "",
    "Digest: ``$($review.result_digest)``",
    "",
    "Static governance only. Live validation and semantic correctness were not claimed."
)
foreach ($finding in $review.blocking_findings) {
    $summary += "- ``$($finding.rule_id)`` $($finding.message) (``$($finding.locator)``)"
}
if ($env:GITHUB_STEP_SUMMARY) {
    $summary | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY -Encoding utf8
} else {
    $summary | Write-Output
}

$sarifFile = ""
if ($env:SESHAT_SARIF -ne "false") {
    $sarifFile = Join-Path $outputRoot "seshat-results.sarif"
    & seshat check --repo $repo --format sarif | Set-Content -LiteralPath $sarifFile -Encoding utf8
}

if ($env:GITHUB_OUTPUT) {
    "outcome=$($review.outcome)" | Add-Content -LiteralPath $env:GITHUB_OUTPUT
    "digest=$($review.result_digest)" | Add-Content -LiteralPath $env:GITHUB_OUTPUT
    "review-json=$reviewFile" | Add-Content -LiteralPath $env:GITHUB_OUTPUT
    "sarif-file=$sarifFile" | Add-Content -LiteralPath $env:GITHUB_OUTPUT
}

exit $reviewExit
