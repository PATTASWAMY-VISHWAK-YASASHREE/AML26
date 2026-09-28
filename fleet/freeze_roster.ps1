# PART 1 of 3 - header, params, roster load, orphan detection, manifest.
# Run the whole file; parts are concatenated in this one file.
#
# WHY POWERSHELL AND NOT plan_batches.py
# The Python interpreter on this box is broken. C:\Program Files\Python313 has no
# Lib\ tree ("Could not find platform independent libraries <prefix>"), and every
# venv on the machine points at an AppData\Local\Programs\Python\Python3xx base
# that no longer exists. `python`, `py` and `python3` all resolve either to the
# 0-byte WindowsApps alias stub or to a deleted base. The .py planners are
# therefore unrunnable, and the fleet cannot be managed without a plan. This
# script does the same job in PowerShell so dispatch is not blocked on an
# unrelated toolchain failure.
#
# WHAT "FREEZE" MEANS HERE
# Country-scope correction renumbered the D-tasks mid-flight, and analysis_out/tasks
# now holds 127 files rather than the original 120, with 5 task JSONs (D071, D072,
# D076, D077, D079) deleted while their .md deliverables survived on disk. Task IDs
# are therefore IMMUTABLE from this point: no more renumbering, no more deletion.
# The manifest records the exact state so future drift is detectable.
#
# A task counts as DELIVERED when the .md path named in its work order exists on
# disk. Same criterion plan_batches.py used, and the right one: a .json sidecar
# alone does not satisfy a work order.
#
# TOLERANCE FOR FILENAME DRIFT. Agents sometimes write a self-descriptive filename
# instead of the exact declared path (observed: D116/D117/D118 all chose
# "remaining_gaps_..." where the work order said "gaps_..."). Re-running that work
# would burn a fleet slot and risk an agent overwriting a good report, so a task
# whose declared path is missing BUT which has exactly one `<id>_*.md` on disk is
# counted as DELIVERED and the drift is reported. This is safe because the task id
# prefix is unique per task, so a glob on it cannot match another task's report.
param(
    [string]$Root = 'C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)',
    [int]$BatchSize = 10
)


$ErrorActionPreference = 'Stop'
$tasksDir     = Join-Path $Root 'analysis_out\tasks'
$findDir      = Join-Path $Root 'analysis_out\findings'
$manifestPath = Join-Path $Root 'analysis_out\roster_manifest.json'
$planPath     = Join-Path $Root 'analysis_out\dispatch_plan.json'

$roster = @()
Get-ChildItem $tasksDir -Filter '*.json' | ForEach-Object {
    $j = Get-Content $_.FullName -Raw | ConvertFrom-Json
    $roster += [PSCustomObject]@{
        id          = $j.id
        family      = $j.family
        title       = $j.title
        deliverable = $j.deliverable
        taskfile    = $_.Name
    }
}
$roster = @($roster | Sort-Object id)

# ----------------------------------------------- orphan deliverables detection
# .md files in findings/ whose task id has no task JSON. These are completed work
# whose work order was destroyed by the renumbering. They are NOT re-dispatched.
$rosterIds = @{}
$roster | ForEach-Object { $rosterIds[$_.id] = $true }
$orphans = @()
Get-ChildItem $findDir -Filter '*.md' | ForEach-Object {
    $b = $_.BaseName
    $oid = $b.Substring(0, [Math]::Min(4, $b.Length))
    if ($oid -match '^[PD]\d{3}$' -and -not $rosterIds.ContainsKey($oid)) {
        $orphans += [PSCustomObject]@{
            id = $oid
            deliverable = $_.FullName.Substring($Root.Length + 1)
        }
    }
}

# ------------------------------------------------------------- status + counts
$drift = @()
foreach ($t in $roster) {
    $st = 'OUTSTANDING'
    $actual = $null
    if (Test-Path (Join-Path $Root $t.deliverable)) {
        $st = 'DELIVERED'
    } else {
        # filename drift: exactly one <id>_*.md on disk means the work was done
        $alts = @(Get-ChildItem $findDir -Filter "$($t.id)_*.md" -ErrorAction SilentlyContinue)
        if ($alts.Count -eq 1) {
            $st = 'DELIVERED'
            $actual = $alts[0].Name
            $drift += [PSCustomObject]@{ id = $t.id; declared = $t.deliverable; actual = $actual }
        }
    }
    $t | Add-Member -NotePropertyName 'status' -NotePropertyValue $st
    $t | Add-Member -NotePropertyName 'actual' -NotePropertyValue $actual
}
$done = @($roster | Where-Object { $_.status -eq 'DELIVERED' })
$todo = @($roster | Where-Object { $_.status -eq 'OUTSTANDING' })

# ------------------------------------------------------------------ manifest
$manifest = [PSCustomObject]@{
    frozen_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    root          = $Root
    batch_size    = $BatchSize
    counts        = [PSCustomObject]@{
        roster             = $roster.Count
        delivered          = $done.Count
        outstanding        = $todo.Count
        orphan_deliverables = $orphans.Count
    }
    note          = 'Task IDs are IMMUTABLE from this point. Do not renumber or delete task JSONs.'
    orphan_deliverables = $orphans
    tasks         = @($roster | ForEach-Object {
        [PSCustomObject]@{
            id = $_.id
            family = $_.family
            title = $_.title
            deliverable = $_.deliverable
            status = $_.status
        }
    })
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content $manifestPath -Encoding UTF8
$hash = (Get-FileHash $manifestPath -Algorithm SHA256).Hash

# -------------------------------------------------------------------- plan
# Priority rationale:
#  rank 0  B-dictionary "audit current X" / "remaining gaps in X"
#  rank 1  A-profile mentioning France
#  rank 2  B-dictionary France mining
#  rank 3  B-dictionary US/India mining
#  rank 4  A-profile non-France
# Audits and gap-closures come first because they establish what a table actually
# does today; a mining task without its audit in hand tends to re-derive ground
# that has already been measured. France A-profile is next because France is the
# only scored country and is absent from training. Bulk descriptive work is last:
# it feeds the report but cannot change _upstream/src/.
function Get-PriorityKey($t) {
    # Rank 0 is reserved for D128, which settles a live contradiction that gates
    # an engineering decision. It is the single highest-value open question.
    # Ranks are zero-padded integers: PowerShell's Sort-Object uses a
    # culture-aware string comparison that strips the leading '-' from '-1',
    # which silently sorted the top-priority task to the END of the queue.
    if ($t.id -eq 'D128') { $r = 0 }
    elseif ($t.family -eq 'B-dictionary') {
        if ($t.title -match '^(audit|remaining gaps)') { $r = 1 }
        elseif ($t.title -match 'France') { $r = 3 }
        else { $r = 4 }
    }
    elseif ($t.title -match 'France') { $r = 2 }
    else { $r = 5 }
    return ('{0:d2}-{1}' -f $r, $t.id)
}

$ordered = @($todo | Sort-Object { Get-PriorityKey $_ })
$batches = @()
for ($i = 0; $i -lt $ordered.Count; $i += $BatchSize) {
    $hi = [Math]::Min($i + $BatchSize - 1, $ordered.Count - 1)
    $slice = @($ordered[$i..$hi])
    $n = [int]($i / $BatchSize) + 1
    $ag = @()
    for ($k = 0; $k -lt $slice.Count; $k++) { $ag += ('b{0:d2}_{1:d2}' -f $n, ($k + 1)) }
    $batches += [PSCustomObject]@{
        batch  = $n
        agents = $ag
        tasks  = @($slice | ForEach-Object {
            [PSCustomObject]@{ id = $_.id; title = $_.title; deliverable = $_.deliverable }
        })
    }
}
$batches | ConvertTo-Json -Depth 6 | Set-Content $planPath -Encoding UTF8

# ------------------------------------------------------------------- report
Write-Output ("roster {0} | delivered {1} | outstanding {2} | orphan deliverables {3}" -f $roster.Count, $done.Count, $todo.Count, $orphans.Count)
Write-Output "manifest SHA256 $hash"
Write-Output ("batches: {0} of <= {1}" -f $batches.Count, $BatchSize)
Write-Output ''
foreach ($b in @($batches | Select-Object -First 3)) {
    Write-Output ("  batch {0,2}: {1}" -f $b.batch, (($b.tasks | ForEach-Object { $_.id }) -join ', '))
}
if ($batches.Count -gt 3) {
    Write-Output '  ...'
    $last = $batches[-1]
    Write-Output ("  batch {0,2}: {1}" -f $last.batch, (($last.tasks | ForEach-Object { $_.id }) -join ', '))
}
if ($orphans.Count -gt 0) {
    Write-Output ''
    Write-Output 'ORPHAN deliverables (work already done, work order lost - NOT re-dispatched):'
    $orphans | ForEach-Object { Write-Output ("  {0} -> {1}" -f $_.id, $_.deliverable) }
}

# ----------------------------------------------------------------- assertions
$seen = @($batches | ForEach-Object { $_.tasks } | ForEach-Object { $_.id })
if ($seen.Count -ne $todo.Count) {
    throw ("plan covers {0} of {1} outstanding tasks" -f $seen.Count, $todo.Count)
}
if (($seen | Select-Object -Unique).Count -ne $seen.Count) { throw 'duplicate task id in plan' }
$byId = @{}
$roster | ForEach-Object { $byId[$_.id] = $_ }
$clash = @($seen | Where-Object {
    $t = $byId[$_]
    (Test-Path (Join-Path $Root $t.deliverable)) -or $t.actual
})
if ($clash.Count -gt 0) { throw ("plan re-dispatches delivered: " + ($clash -join ', ')) }
Write-Output ''
Write-Output ("verified: {0} unique outstanding tasks, full coverage, no duplicates, no delivered task re-planned" -f $seen.Count)
if ($drift.Count -gt 0) {
    Write-Output ''
    Write-Output ("FILENAME DRIFT: {0} task(s) delivered under a self-chosen name, not the declared path." -f $drift.Count)
    Write-Output 'Counted as DELIVERED so the work is not repeated. The task JSONs still name the old path.'
    $drift | ForEach-Object { Write-Output ("  {0}: declared '{1}' -> actual '{2}'" -f $_.id, (Split-Path $_.declared -Leaf), $_.actual) }
}

