# Validate and depth-scan every sidecar in analysis_out/findings/.
#
# WHY THIS EXISTS
# Two sidecars in this project have already shipped broken, in the same way:
#   - D079 shipped with an orphaned fragment appended AFTER the closing brace.
#   - D126 has a duplicated block and a misplaced closing brace.
# In both cases the file EXISTED and had a non-zero size, so a `Test-Path` or a
# file-size check reported success. Only a real parse catches them. This script is
# the guard that should have run after every agent finished.
#
# WHEN A SIDECAR FAILS: the .md deliverable is the authoritative artefact and the
# sidecar is a convenience index. Do NOT delete the sidecar - report it, because a
# missing sidecar and a corrupt one are different failures and an aggregator needs
# to know which it is looking at.
param([string]$Root = 'C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)')

# ARITHMETIC CROSS-CHECK, added after D120 shipped a valid-JSON sidecar whose
# derived TOTAL disagreed with its own components (headline said 6,192 = sum of
# six corruptions; the correct sum was 5,192). Every individual field was
# correct and the file parsed cleanly, so validate_sidecars.ps1 could never have
# caught it. D120 found it by recomputing every expression in the document.
#
# This scans sidecars for the `{"total": N}` idiom - a very common shape when an
# agent reports a part/whole breakdown - and verifies that `total` equals the SUM
# of the sibling per-part values. It is deliberately conservative: it only reports
# a SUSPECT, never auto-fails, because a legitimate total need not be a plain sum
# (subsets, disjoint unions, and deduplicated counts are all valid). A human or the
# owning agent must adjudicate each hit.

$ErrorActionPreference = 'Continue'
$findDir = Join-Path $Root 'analysis_out\findings'
$files = @(Get-ChildItem $findDir -Filter '*.json' | Sort-Object Name)
$ok = 0
$bad = @()

foreach ($f in $files) {
    $raw = Get-Content $f.FullName -Raw
    $err = $null
    try { $null = $raw | ConvertFrom-Json -ErrorAction Stop } catch { $err = $_.Exception.Message }

    if (-not $err) { $ok++; continue }

    # Locate the failure by tracking bracket depth outside of string literals.
    # A duplicate key or a stray closing brace shows up as depth returning to 0
    # early (trailing content) or depth going negative (an extra close).
    $depth = 0; $inStr = $false; $esc = $false
    $firstNeg = -1; $firstZero = -1
    for ($i = 0; $i -lt $raw.Length; $i++) {
        $c = $raw[$i]
        if ($esc) { $esc = $false; continue }
        if ($c -eq '\') { $esc = $true; continue }
        if ($c -eq '"') { $inStr = -not $inStr; continue }
        if ($inStr) { continue }
        if ($c -eq '{' -or $c -eq '[') { $depth++ }
        elseif ($c -eq '}' -or $c -eq ']') {
            $depth--
            if ($depth -lt 0 -and $firstNeg -lt 0) { $firstNeg = $i }
        }
    }
    $line = ($raw.Substring(0, [Math]::Min(400, $raw.Length)) -split "`n").Count
    $bad += [PSCustomObject]@{
        file      = $f.Name
        bytes     = $f.Length
        error     = $err
        negBrace  = $firstNeg
        finalDepth = $depth
    }
    Write-Output ("FAIL  {0}  ({1} bytes)" -f $f.Name, $f.Length)
    Write-Output ("      {0}" -f $err)
    if ($firstNeg -ge 0) { Write-Output ("      extra closing brace at char {0}" -f $firstNeg) }
    if ($depth -ne 0)    { Write-Output ("      net depth {0} (0 = balanced)" -f $depth) }
}

Write-Output ''
Write-Output ("sidecars: {0} total, {1} valid, {2} INVALID" -f $files.Count, $ok, $bad.Count)

# ---------------------------------------------------------------- arithmetic
# Walk each parsed sidecar; for every object that has a "total" key plus other
# numeric siblings, check whether total == sum(siblings). Report only MISMATCHES.
Write-Output ''
Write-Output 'arithmetic cross-check (total vs sum of sibling parts):'
$suspect = 0
$checked = 0

function Test-Totals($node, $path) {
    if ($null -eq $node) { return }
    # A PSCustomObject is IEnumerable (PSObject wraps a dictionary), so it MUST be
    # excluded before the array branch or the recursion never reaches the scalar
    # members. That ordering bug is why the first run reported "checked 0".
    $isObj = $node -is [System.Management.Automation.PSCustomObject]
    if (-not $isObj -and $node -is [System.Collections.IEnumerable] -and
        -not ($node -is [string]) -and -not ($node -is [System.Collections.IDictionary])) {
        $i = 0
        foreach ($item in $node) { Test-Totals $item "$path[$i]"; $i++ }
        return
    }
    $props = @($node.PSObject.Properties)
    if ($props.Count -gt 2) {
        $tprop = $props | Where-Object { $_.Name -eq 'total' } | Select-Object -First 1
        if ($tprop -and $tprop.Value -is [ValueType]) {
            $script:checked++
            $sum = 0.0; $n = 0
            foreach ($p in $props) {
                if ($p.Name -eq 'total') { continue }
                # Skip percentages/rates/notes: they are not additive parts, and
                # including them produced a false positive on D073/D128
                # (france_rows summed 15.31 into 1,694,445 and reported a 100-row
                # error that did not exist). A "total" is only comparable to counts.
                if ($p.Name -match '%|pct|rate|share|score|note|scope|verdict|status') { continue }
                $v = $p.Value
                if ($v -is [int] -or $v -is [long] -or $v -is [double] -or $v -is [decimal]) {
                    $sum += [double]$v; $n++
                }
            }
            # only meaningful when several numeric parts are present
            if ($n -ge 3) {
                $diff = [math]::Abs($sum - [double]$tprop.Value)
                if ($diff -gt 0.5) {
                    $script:suspect++
                    Write-Output ("  SUSPECT {0}{1}: total={2} but parts sum to {3} (diff {4}, {5} numeric parts)" -f `
                        $script:curFile, $path, $tprop.Value, $sum, $diff, $n)
                }
            }
        }
    }
    foreach ($p in $node.PSObject.Properties) { Test-Totals $p.Value "$path.$($p.Name)" }
}

foreach ($f in $files) {
    $script:curFile = $f.Name
    try {
        $o = Get-Content $f.FullName -Raw | ConvertFrom-Json -ErrorAction Stop
        Test-Totals $o ''
    } catch { }
}
Write-Output ("  checked {0} 'total' fields, {1} suspect" -f $checked, $suspect)
if ($suspect -gt 0) {
    Write-Output '  NOTE: a suspect is NOT necessarily wrong - subsets and deduplicated counts legitimately'
    Write-Output '  differ from a plain sum. Adjudicate against the .md, which is authoritative.'
}
Write-Output ''
if ($bad.Count -gt 0 -or $suspect -gt 0) { exit 1 }
