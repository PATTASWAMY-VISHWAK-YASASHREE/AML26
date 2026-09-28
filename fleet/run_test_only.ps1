<#
.SYNOPSIS
  Memory-safe, disk-safe, resumable TEST-ONLY runner for the entity-resolution pipeline.

.DESCRIPTION
  Runs the surviving chain on a machine with ~6.8 GB free disk and ~1 GB free RAM:

      convert (test)  ->  prep (test)  ->  run_blocking test
        ->  [per country: build_features test -> make_submission -> delete]
        ->  make_submission FINALIZE  ->  validate_submission.py

  Six upstream steps are SKIPPED because _upstream/models ships the five trained
  files make_submission.py needs; copying them in arms CF=True (line 15) and
  supplies the cross-fitted models, so learn_translit / build_features train /
  trainT / trainRest / select_T / crossfit are never needed.  Their combined disk
  cost was 3.5-14 GB per step; skipping them is what makes this run possible at all.

  build_features and make_submission run ONE COUNTRY AT A TIME and each country's
  multi-GB feature parquet is deleted as soon as it has been scored.  That is
  mandatory, not an optimisation: all three countries together need ~8.9 GB of
  feature parquet, which does not fit in 6.8 GB.

  Every stage checks for its own output and skips when it is present, so the script
  can be killed and re-run at any point.  Markers are written only after the work
  they mark is on disk, so a killed run repeats a stage rather than trusting it.

.PARAMETER From
  Resume point.  One of: preflight, convert, prep, blocking, features, finalize,
  validate, all (default: all).

.PARAMETER StopAfter
  Run stages only up to and including this one, then stop.  Combined with -From this
  gives one stage per invocation so disk can be watched between stages:
      -From convert -StopAfter convert     (convert only)
      -From prep    -StopAfter prep        (prep only)
  Default: all, i.e. run to the end.

.PARAMETER MaxCountries
  In the features stage, process at most this many countries and then stop.  The
  features stage is the long, disk-hungry one, so this lets you run one country per
  invocation.  0 (default) means all of them.  Already-completed countries are
  skipped before the count is taken, so this is safe to repeat.

.PARAMETER Countries
  Comma-separated subset of countries for the features stage.  Default: all,
  ordered largest-S1-first.

.PARAMETER KeepIntermediates
  Do NOT delete feature/candidate parquet between stages.  Needs roughly +9 GB and
  will normally fail on this disk.  Debugging aid only.

.PARAMETER PreflightOnly
  Print the environment check and the full disk plan, then exit without writing.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run_test_only.ps1 -PreflightOnly
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\run_test_only.ps1 -From convert
#>
[CmdletBinding()]
param(
  [string]$From = "all",
  [string]$StopAfter = "all",
  [int]$MaxCountries = 0,
  [string]$Countries = "",
  [switch]$KeepIntermediates,
  [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------------------------------- paths
$Base      = $PSScriptRoot
$Src       = Join-Path $Base "run_src\src"
$Dataset   = Join-Path $Base "amazon_ml_2026_research\student_resource\dataset"
$Validator = Join-Path $Base "amazon_ml_2026_research\student_resource\utils\validate_submission.py"
$Work      = Join-Path $Base "work_test"
$Out       = Join-Path $Base "output"
$Models    = Join-Path $Base "_upstream\models"
$Ttd       = Join-Path $Base "_ttd"
$LogDir    = Join-Path $Base "run_logs"
$Py        = Join-Path $Base ".venv\Scripts\python.exe"

# --------------------------------------------------------------------- env settings
# Thread/RAM env vars come from _ttd\env_runtime.ps1, the authoritative list, so this
# script and the rest of the fleet agree.  POLARS_MAX_THREADS must be set BEFORE polars
# is first imported, i.e. in the process environment, which is why it is dot-sourced
# here rather than set inside Python.
$envRuntime = Join-Path $Ttd "env_runtime.ps1"
if (Test-Path $envRuntime) {
  # env_runtime.ps1 runs $args[0] if it is given one; blank $args so a dot-source only
  # sets the environment and never launches anything.
  $savedArgs = $args
  $args = @()
  . $envRuntime
  $args = $savedArgs
  "  [ok] thread env from _ttd\env_runtime.ps1 (POLARS_MAX_THREADS=$($env:POLARS_MAX_THREADS), OMP_NUM_THREADS=$($env:OMP_NUM_THREADS))"
} else {
  # Fallback: the same values, in case the helper is unavailable.
  $env:PYTHONDONTWRITEBYTECODE  = "1"
  $env:POLARS_MAX_THREADS       = "2"
  $env:OMP_NUM_THREADS          = "2"
  $env:OPENBLAS_NUM_THREADS     = "2"
  $env:MKL_NUM_THREADS          = "2"
  $env:NUMEXPR_NUM_THREADS      = "2"
  $env:VECLIB_MAXIMUM_THREADS   = "2"
  $env:OMP_THREAD_LIMIT         = "2"
  $env:RAYON_NUM_THREADS        = "2"
  "  [warn] _ttd\env_runtime.ps1 not found - used the inlined equivalent list"
}

# Pipeline tunables specific to this runner.
# FEAT_CHUNK=50000 is build_features' pairs-per-chunk: it sets peak RSS, not results
#   (chunking is by query id, so the rows produced are identical to CHUNK=600000).
$env:FEAT_CHUNK              = "50000"
$env:PREP_NPROC              = "1"
$env:PREP_CHUNK              = "20000"
# prep streams in PREP_CHUNK batches but writes them in ~200k-row row groups, and
# combine_chunks()s each group first.  One row group per 20k batch measured 25% larger
# on disk than the old single-shot write; this recovers most of that for ~18 MB of RAM.
$env:PREP_ROWGROUP_ROWS      = "200000"
$env:CONVERT_BATCH           = "250000"
$env:CONVERT_SPLITS          = "test"
$env:CONVERT_RESUME          = "1"
$env:PREP_RESUME             = "1"
$env:FEAT_RESUME             = "1"

# ------------------------------------------------------------- disk model (MB)
# Every figure is either MEASURED on the real test files or derived from the
# upstream README's own "30.5 candidates per S1" and the 7.40 GB feature total.
$script:Disk = @{
  data_parquet   = 522    # MEASURED  convert(test): 72.9 + 223.3 + 226.0
  norm_parquet   = 1030   # MEASURED  prep expansion x1.97 -> 143.8 / 440 / 446
  test_s1        = 148    # MEASURED after run_blocking
  test_q         = 870    # MEASURED after run_blocking
  cand_all       = 976    # MEASURED: India 494.3 + US 253.4 + France 228.6 (81,970,154 rows)
  idf            = 30
  models         = 35     # the 5 shipped files LF-normalised: 36,261,577 bytes = 34.6 MiB
  bytes_per_pair = 150    # 7.40 GB / 52.8M pairs; 52,860,151 pairs were MEASURED on test
  pred_per_pair  = 12     # rid u32 + s1 u32 + p1 f32
  best_per_query = 16     # rid + s1 + p1 + p2
  queries_per_s1 = 5.756  # 9,969,589 queries / 1,732,544 S1
  pairs_per_s1   = 30.5   # upstream README: 30.5 candidates per S1 after retrieval
}

# ------------------------------------------------------------------------- helpers
function Get-FreeDiskMB { [math]::Round((Get-PSDrive -Name C).Free / 1MB, 0) }

function Get-FreeRAMMB {
  $os = Get-CimInstance Win32_OperatingSystem
  [math]::Round($os.FreePhysicalMemory / 1KB, 0)
}

function Format-Budget {
  param([string]$Stage, [string]$Note = "")
  "  {0,-16} freeDisk={1,6} MB   freeRAM={2,5} MB   {3}" -f $Stage, (Get-FreeDiskMB), (Get-FreeRAMMB), $Note
}

function Write-Banner {
  param([string]$Text)
  ""
  "=============================================================================="
  $Text
  "  {0}   freeDisk={1} MB   freeRAM={2} MB" -f (Get-Date -Format "HH:mm:ss"), (Get-FreeDiskMB), (Get-FreeRAMMB)
  "=============================================================================="
}

function New-Dir([string]$Path) {
  if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null }
}

function Get-DirMB([string]$Path) {
  if (-not (Test-Path $Path)) { return 0 }
  $s = (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
  if ($null -eq $s) { return 0 }
  [math]::Round($s / 1MB, 1)
}

# Delete a file and report what it gave back.  Never touches anything outside $Work.
function Remove-WorkFile {
  param([string]$Path, [switch]$Quiet)
  if (-not (Test-Path $Path)) { return 0 }
  $mb = [math]::Round((Get-Item $Path).Length / 1MB, 1)
  Remove-Item $Path -Force
  if (-not $Quiet) { "  [free] {0,-34} -{1,7} MB  (now {2} MB free)" -f (Split-Path $Path -Leaf), $mb, (Get-FreeDiskMB) }
  return $mb
}

# Abort cleanly BEFORE filling the disk, naming exactly what did not fit.
function Assert-FreeDisk {
  param([int]$NeedMB, [string]$What)
  $free = Get-FreeDiskMB
  if ($free -lt $NeedMB) {
    ""
    "  [ABORT] not enough disk for $What"
    "          need {0,6} MB   have {1,6} MB   (short by {2} MB)" -f $NeedMB, $free, ($NeedMB - $free)
    "          Nothing was written and nothing was deleted. Re-run after freeing space."
    throw "insufficient disk for $What"
  }
}

# Defence in depth against the CRLF model bug.  _ttd\stage_models.ps1 already
# normalises and load-tests the models, but if a stale/corrupt copy is ever left in
# the work dir by something else, lightgbm aborts the whole process rather than
# raising, so the run dies at make_submission with no Python traceback.  This scans
# for a stray CR and refuses to continue, which costs a second and fails cleanly.
function Assert-StagedModelsClean {
  $bad = @()
  foreach ($mf in @("model_stage1_f0.txt", "model_stage1_f1.txt", "model_stage2_cf.txt")) {
    $p = Join-Path $Work $mf
    if (-not (Test-Path $p)) { $bad += "$mf (missing)"; continue }
    $bytes = [System.IO.File]::ReadAllBytes($p)
    $cr = 0
    foreach ($by in $bytes) { if ($by -eq 13) { $cr++ } }
    if ($cr -gt 0) { $bad += "$mf ($cr stray CR bytes - CRLF-corrupted)" }
  }
  if ($bad.Count -gt 0) {
    ""
    "  [ABORT] the staged LightGBM models are CRLF-corrupted:"
    $bad | ForEach-Object { "            - $_" }
    "          lgb.Booster() would abort with 'Model format error, expect a tree here'"
    "          and exit -1073740791. Re-run stage 0b to re-stage them with LF endings."
    throw "CRLF-corrupted staged models"
  }
  # The 2 .json meta files are single-line and carry no CR, so they need no
  # normalisation; lf_copy.py still copies them, byte-identically.
  foreach ($jf in @("model_stage1_cf.json", "model_stage2_cf.json")) {
    if (-not (Test-Path (Join-Path $Work $jf))) { throw "missing model meta file $jf in $Work" }
  }
  "  [ok] staged models have 0 stray CR bytes"
}


# Run one python script from run_src/src, tee-ing output to run_logs/<Name>.log.
function Invoke-Stage {
  param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string[]]$ArgList,
    [string[]]$ExtraEnv = @()
  )
  foreach ($kv in $ExtraEnv) {
    $pair = $kv.Split("=", 2)
    Set-Item -Path "Env:$($pair[0])" -Value $pair[1] -Scope Script
  }
  $log = Join-Path $LogDir "$Name.log"
  Write-Banner "STAGE $Name   $($ArgList -join ' ')"
  "  log -> $log"
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  # Guard the slice: with a single element, 1..0 would reverse and re-pass the script name.
  $rest = if ($ArgList.Count -gt 1) { @($ArgList[1..($ArgList.Count - 1)]) } else { @() }

  # A native command's stderr is merged into this stream by 2>&1, and with
  # $ErrorActionPreference='Stop' PowerShell turns EACH such line into a terminating
  # NativeCommandError.  prep died like this: a harmless polars DeprecationWarning on
  # stderr killed run_test_only.ps1 itself, mid-stage, with no explanation.  So
  # stderr must be non-fatal here; the child's real exit code and the artifact check
  # below are what decide success.
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & $Py (Join-Path $Src $ArgList[0]) @rest 2>&1 | Tee-Object -FilePath $log
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prevEap
  }
  $sw.Stop()
  ""
  "  [done] $Name exit=$code  {0} min  freeDisk={1} MB  freeRAM={2} MB" -f `
      [math]::Round($sw.Elapsed.TotalMinutes, 1), (Get-FreeDiskMB), (Get-FreeRAMMB)
  if ($code -ne 0) { Stop-WithLogDetail $Name $log $code }
}

# Loud, self-explanatory failure.  A stage that dies with no output and no traceback is
# indistinguishable from one that never ran, so the log tail is always printed.
function Stop-WithLogDetail {
  param([string]$Name, [string]$Log, [int]$Code)
  ""
  "  " + ("=" * 74)
  "  [HARD FAILURE] stage '$Name' exited with code $Code"
  "  " + ("=" * 74)
  if ($Code -eq 3221226505 -or $Code -eq -1073740791) {
    "  That is 0xC0000409 STATUS_STACK_BUFFER_OVERRUN / abort. A process that is killed"
    "  (OOM, commit-limit, or a native abort such as LightGBM's model parser) exits"
    "  like this with NO Python traceback. It is not a bug in the script."
  }
  "  Last 30 lines of $Log :"
  if (Test-Path $Log) { Get-Content $Log -Tail 30 | ForEach-Object { "    | $_" } }
  else { "    (log file was never created)" }
  "  free disk {0} MB, free RAM {1} MB, work/ = {2} MB" -f (Get-FreeDiskMB), (Get-FreeRAMMB), (Get-DirMB $Work)
  "  " + ("=" * 74)
  throw "stage $Name failed (exit $Code) - see the log tail above"
}

# Assert the artifacts a stage was supposed to produce actually exist.  This is what
# turns a silent death into a visible one, and catches a stage that "succeeds" while
# writing nothing (which is exactly what prep did).
#
# $PreExisted maps path -> $true when the file was already there BEFORE the stage ran.
# A file that was neither pre-existing nor created is one the stage legitimately skipped
# (resume), so it is not a failure; a file that EXISTED and has since vanished is.
function Assert-Artifacts {
  param([string]$Name, [string[]]$Paths, [hashtable]$RowCounts = @{}, [hashtable]$PreExisted = @{})
  $bad = 0
  $skip = 0
  foreach ($p in $Paths) {
    $now = Test-Path $p
    $was = $false
    if ($PreExisted -and $PreExisted.ContainsKey($p)) { $was = [bool]$PreExisted[$p] }
    if (-not $now -and -not $was) { $skip++; continue }
    $args2 = @((Join-Path $Src "check_parquet.py"), $p)
    if ($RowCounts -and $RowCounts.ContainsKey($p)) { $args2 += [string]$RowCounts[$p] }
    $o = & $Py @args2 2>&1
    $rc = $LASTEXITCODE
    $o | ForEach-Object { "    $_" }
    if ($rc -ne 0) { $bad++ }
  }
  if ($skip -gt 0) {
    "    [note] $skip file(s) neither pre-existing nor newly written - the stage skipped them (resume)"
  }
  if ($bad -gt 0) {
    ""
    "  [HARD FAILURE] stage '$Name' reported success but $bad expected output file(s) are"
    "  missing, empty, truncated, or have the wrong row count / column order."
    "  Nothing downstream can be trusted after this - fix it and re-run the stage."
    throw "stage $Name produced unusable output ($bad bad file(s))"
  }
}

# Countries in the work dir with their S1 counts and their post-filter pair counts,
# smallest-feature-parquet first.  Falls back to the MEASURED S1 counts when
# test_s1.parquet does not exist yet, so -PreflightOnly still prints a full plan.
$script:KnownS1 = @(
  [pscustomobject]@{ Name = "France"; Count = [int64]259452;  Pairs = [int64]10211440 },
  [pscustomobject]@{ Name = "US";    Count = [int64]663106;  Pairs = [int64]13945347 },
  [pscustomobject]@{ Name = "India"; Count = [int64]809986;  Pairs = [int64]28703364 }
)
function Get-S1Counts {
  $p = Join-Path $Work "test_s1.parquet"
  if (-not (Test-Path $p)) { return $script:KnownS1 }
  $rows = @()
  foreach ($line in (& $Py (Join-Path $Src "country_counts.py") $Work)) {
    $f = $line -split "`t"
    if ($f.Count -ge 2) {
      $pr = 0; if ($f.Count -ge 3) { $pr = [int64]$f[2] }
      $rows += [pscustomobject]@{ Name = $f[0]; Count = [int64]$f[1]; Pairs = $pr }
    }
  }
  if ($rows.Count -eq 0) { return $script:KnownS1 }
  return $rows
}

# work/data/*.parquet is DEAD once run_blocking has built test_s1/test_q: 522 MB, which
# is the difference between the features stage fitting and not.  Idempotent, and called
# from the prep, blocking AND features stages so it happens even when prep is skipped.
function Remove-StaleDataDir {
  $d = Join-Path $Work "data"
  if (-not (Test-Path $d)) { return 0 }
  $normLeft = @(Get-ChildItem $Work -Filter "*_norm.parquet" -File -ErrorAction SilentlyContinue).Count
  if ($normLeft -gt 0 -and -not (Test-Path (Join-Path $Work "test_s1.parquet"))) {
    "  [skip] work/data kept: *_norm.parquet still present and blocking has not run"
    return 0
  }
  $f0 = Get-FreeDiskMB
  Write-Banner "RECLAIM  work/data/*.parquet  (dead once blocking has built test_s1/test_q)"
  $freed = 0
  Get-ChildItem $d -Filter *.parquet -File -ErrorAction SilentlyContinue | ForEach-Object { $freed += Remove-WorkFile $_.FullName }
  "  reclaimed {0} MB;  free disk {1} -> {2} MB" -f $freed, $f0, (Get-FreeDiskMB)
  return $freed
}

# ------------------------------------------------------------------- stage ordering
# preflight 0, convert 1, prep 2, blocking 3, features 4, finalize 5, validate 6
$Stages = [ordered]@{ preflight = 0; convert = 1; prep = 2; blocking = 3; features = 4; finalize = 5; validate = 6 }
$StageNames = @($Stages.Keys)

$StartAt = 0
if ($From -ne "all") {
  if (-not $Stages.Contains($From)) {
    throw "unknown -From '$From'. Use one of: $($StageNames -join ', '), all"
  }
  $StartAt = $Stages[$From]
}
$StopAt = 99
if ($StopAfter -ne "all") {
  if (-not $Stages.Contains($StopAfter)) {
    throw "unknown -StopAfter '$StopAfter'. Use one of: $($StageNames -join ', '), all"
  }
  $StopAt = $Stages[$StopAfter]
}
if ($StopAt -lt $StartAt) {
  throw "-StopAfter '$StopAfter' ($StopAt) is before -From '$From' ($StartAt) - nothing would run"
}

# A stage runs when it falls inside [StartAt, StopAt].
function Stage-Due([string]$Name) { return ($Stages[$Name] -ge $StartAt) -and ($Stages[$Name] -le $StopAt) }

New-Dir $Work
New-Dir (Join-Path $Work "data")
New-Dir $Out
New-Dir $LogDir

Write-Banner "TEST-ONLY RUNNER   base=$Base"
"  work   = $Work"
"  output = $Out"
"  resume = $From"
"  python = $Py"

# ============================================================ STAGE 0: preflight
if (Stage-Due "preflight") {
  Write-Banner "STAGE 0  preflight"
  if (-not (Test-Path $Py))         { throw "python not found: $Py" }
  if (-not (Test-Path $Src))        { throw "run_src/src not found: $Src" }
  if (-not (Test-Path $Validator))  { throw "validator not found: $Validator" }
  if (-not (Test-Path $Dataset))    { throw "dataset not found: $Dataset" }
  "  [ok] python, run_src, dataset and validator all present"

  & $Py -c "import polars, numpy, lightgbm, rapidfuzz, pyarrow; print('  [ok] deps: polars %s  numpy %s  lightgbm %s' % (polars.__version__, numpy.__version__, lightgbm.__version__))"
  if ($LASTEXITCODE -ne 0) { throw "python dependency import failed" }

  # ---- Stage the 5 trained models.  This is what arms CF=True in make_submission.py:15
  # and lets us skip learn_translit, build_features train/trainT/trainRest, select_T
  # and crossfit.  Without them the run cannot produce a scored submission.
  #
  # CRITICAL: do NOT Copy-Item these.  _upstream was cloned with core.autocrlf=true and
  # no .gitattributes, so the three LightGBM .txt files are checked out CRLF-corrupted
  # (every one of the 9,511/9,188/12,725 lines ends in CR).  lgb.Booster(model_file=...)
  # cannot parse the stray CR and ABORTS THE PROCESS (not a Python exception) with
  #   [LightGBM] [Fatal] Model format error, expect a tree here
  # and exit code -1073740791 (0xC0000409) - killing make_submission outright.
  # _ttd\stage_models.ps1 does the CRLF->LF normalisation and then proves the staged
  # models load (num_feature 63/63/85) before any expensive work starts.  _upstream
  # itself is never modified: the copy is one-way, into the work dir.
  Write-Banner "STAGE 0b  stage the 5 models with CRLF->LF normalisation (arms CF=True)"
  $stageModels = Join-Path $Ttd "stage_models.ps1"
  if (-not (Test-Path $stageModels)) {
    throw "required helper not found: $stageModels - the shipped models are CRLF-corrupted and a plain copy hard-crashes lightgbm"
  }
  & powershell -ExecutionPolicy Bypass -NoProfile -File $stageModels $Work
  if ($LASTEXITCODE -ne 0) { throw "stage_models.ps1 failed (exit $LASTEXITCODE) - models are not usable, stopping before any data is written" }
  Assert-StagedModelsClean
  "  [ok] staged models are LF-clean and verified loadable"
  "  [ok] make_submission.py:15 will take the CF=True branch"
  # The real contract is not just the column COUNT (63 stage-1 / 85 stage-2) but the
  # column ORDER: make_submission selects features with m1_meta["cols"] / m2_meta["cols"],
  # so if the booster's feature_name() order disagreed with the json, predictions would
  # be silently scrambled rather than erroring.  Compare names, not just counts.
  & $Py (Join-Path $Src "check_model_contract.py") $Work
  if ($LASTEXITCODE -ne 0) { throw "model/feature-name contract check FAILED - stopping before any data is written" }

  # ---- PREFLIGHT VALIDATOR on whatever output exists right now.
  Write-Banner "STAGE 0c  PREFLIGHT validate_submission.py on the existing output files"
  "  Note what this does NOT do: the official validator checks FORMAT only. Today's"
  "  wholly empty submission (1,732,544 rows, every id blank) PASSES it with exit 0,"
  "  so a green validator is NOT evidence that the run produced anything scoreable."
  "  Stage 6b (check_nonempty.py) is the check that actually catches that."
  $pre = & $Py $Validator --matching (Join-Path $Out "matching_results.tsv") `
                        --candidate (Join-Path $Out "candidate_pairs.tsv") `
                        --test-dir (Join-Path $Dataset "test") 2>&1
  $preCode = $LASTEXITCODE
  $pre | Select-Object -First 14 | ForEach-Object { "    $_" }
  "  [preflight validator] exit=$preCode"
  "  NOTE: the official validator checks FORMAT only. Today's completely empty"
  "  submission passes it with exit 0, so it cannot detect a zero-scoring run."
  "  That is what check_nonempty.py is for:"
  $ne = & $Py (Join-Path $Src "check_nonempty.py") $Out 2>&1
  $neCode = $LASTEXITCODE
  $ne | ForEach-Object { "    $_" }
  "  [preflight non-empty check] exit=$neCode  (1 is EXPECTED today - the output is empty)"



  # ---- the disk plan
  Write-Banner "DISK PLAN   (all figures MB; measured ones marked MEASURED)"
  $mdl = $script:Disk
  "  A. convert  (test split only)"
  "       write  work/data/*.parquet                        +{0,6}" -f $mdl.data_parquet
  "  B. prep     (test split only)"
  "       write  work/*_norm.parquet                        +{0,6}" -f $mdl.norm_parquet
  "       peak   data + norm                              {0,6}" -f ($mdl.data_parquet + $mdl.norm_parquet)
  "       RECLAIM delete work/data  (nothing downstream reads it)  -{0,5}" -f $mdl.data_parquet
  "  C. run_blocking test"
  "       write  test_s1 {0} + test_q {1} + cand_<country> {2}   +{3,6}" -f $mdl.test_s1, $mdl.test_q, $mdl.cand_all, ($mdl.test_s1 + $mdl.test_q + $mdl.cand_all)
  "       transient test_cand.parquet (concat) {0} + _tmp_q_*.parquet   -> run_blocking removes the tmp_q itself" -f $mdl.cand_all
  "       RECLAIM delete test_cand.parquet  (build_features reads the per-country files)  -{0,5}" -f $mdl.cand_all
  "       RECLAIM delete *_norm.parquet     (test_s1/test_q are already built from them)  -{0,5}" -f $mdl.norm_parquet
  $baseMB = $mdl.test_s1 + $mdl.test_q + $mdl.cand_all + $mdl.idf + $mdl.models
  "       -> steady-state base entering the country loop   {0,6}" -f $baseMB
  ""
  "  D. per country, SMALLEST feature parquet first (see country_counts.py):"
  "       build_features -> make_submission -> delete feat + pred + that country's cand"
  "       feature parquet = pairs * {0} B, where pairs is the MEASURED count surviving" -f $mdl.bytes_per_pair
  "       the same bscore >= 0.3*btop filter that build_features applies."
  $s1 = Get-S1Counts
  $cur = $baseMB
  $peak = $baseMB
  $totFeat = 0
  foreach ($c in $s1) {
    $pairs = if ($c.Pairs -gt 0) { $c.Pairs } else { [math]::Round($c.Count * $mdl.pairs_per_s1) }
    $feat  = [math]::Round($pairs * $mdl.bytes_per_pair / 1MB, 0)
    $pred  = [math]::Round($pairs * $mdl.pred_per_pair / 1MB, 0)
    $best  = [math]::Round($c.Count * $mdl.queries_per_s1 * $mdl.best_per_query / 1MB, 0)
    $totFeat += $feat
    $step = $cur + $feat + $pred + $best
    $peak = [math]::Max($peak, $step)
    "         {0,-8} S1={1,9}  pairs={2,10}  feat={3,6}  pred={4,5}  best={5,4}   held+peak={6,6}" -f `
        $c.Name, $c.Count, $pairs, $feat, $pred, $best, $step
    "                  then delete feat + pred + its cand part     -{0,6}  (best_{1}.parquet is kept)" -f ($feat + $pred), $c.Name
    $cur = $cur + $best
  }
  ""
  "         feature parquet, all 3 countries                   {0,6}" -f $totFeat
  "         PEAK work/ CONTENT for the whole run                {0,6}" -f $peak
  # The peak is a work/ CONTENT figure, so what matters is free disk MINUS the GROWTH
  # above the base - not free disk minus the peak.  work/ currently holds more than the
  # steady-state base (work/data is 522 MB of it, dead once blocking has run, plus the
  # *_norm.parquet until they are reclaimed), and that excess is reclaimable, so it
  # counts towards "available".  Measured from the directory, so nothing is double
  # counted: work/data is INSIDE work/ and must not be added a second time.
  $holdNow = Get-DirMB $Work
  $pending = [math]::Round($holdNow - $baseMB, 0)
  if ($pending -lt 0) { $pending = 0 }
  $need = $peak - $baseMB
  $have = (Get-FreeDiskMB) + $pending
  $dataMB = 0
  $dDir = Join-Path $Work "data"
  if (Test-Path $dDir) { $dataMB = [math]::Round((Get-DirMB $dDir), 0) }
  "         growth in work/ above the base (the real requirement) {0,6}" -f $need
  "         free disk now                                      {0,6}" -f (Get-FreeDiskMB)
  "         work/ holds {0} MB, base is {1} MB -> reclaimable excess +{2,5}" -f $holdNow, $baseMB, $pending
  if ($dataMB -gt 0) { "           (of which work/data alone is {0} MB, deleted automatically)" -f $dataMB }
  "         AVAILABLE                                         {0,6}" -f $have
  if ($need -gt $have) {
    "         *** INSUFFICIENT by {0} MB ***" -f ($need - $have)
    "         Reclaim amazon_ml_2026_research\.tmp (4309 MB, read-only - owner only),"
    "         or free {0} MB elsewhere, before starting the features stage." -f ($need - $have)
  } elseif (($have - $need) -lt 500) {
    "         headroom                                          {0,6} MB  ({1}%)  <-- TOO TIGHT" -f `
        ($have - $need), [math]::Round(100 * ($have - $need) / $have, 0)
    "         This is inside the error bar of the {0} B/pair feature-size estimate." -f $mdl.bytes_per_pair
    "         Do NOT start the last country (the biggest) on this margin. Free at least"
    "         1000 MB more - the 4309 MB orphaned spill is the obvious candidate."
  } else {
    "         headroom                                          {0,6} MB  ({1}%)" -f `
        ($have - $need), [math]::Round(100 * ($have - $need) / $have, 0)
    "         The tightest moment is the LAST country in the list above."
  }
  ""
  "  E. finalize + validate                                  small (the 2 TSVs are ~24 MB each)"
  ""
  "  WITHOUT the per-country loop the feature parquet alone is {0} MB on top of a" -f $totFeat
  "  {0} MB base = {1} MB, which does NOT fit in {2} MB. The per-country loop is" -f $baseMB, ($totFeat + $baseMB), (Get-FreeDiskMB)
  "  therefore mandatory, not an optimisation."
  ""
  "  ORPHANED SPILL - read-only per fleet rules, NOT touched by this script:"
  $spill = Join-Path $Base "amazon_ml_2026_research\.tmp"
  if (Test-Path $spill) {
    "     {0}" -f $spill
    "     {0} MB of duckdb_temp_storage_*.tmp (7 files, 2026-09-25 20:31, from a killed run)." -f (Get-DirMB $spill)
    "     Reclaimable ONLY if the fleet owner deletes it; that would lift the peak"
    "     headroom from {0} MB to about {1} MB. The plan above does not need it." -f `
        ((Get-FreeDiskMB) - $peak), ((Get-FreeDiskMB) + (Get-DirMB $spill) - $peak)
  }
  ""
  Format-Budget "after-preflight" "nothing written yet"
}

if ($PreflightOnly) {
  Write-Banner "PreflightOnly - stopping before any stage that writes data"
  exit 0
}


# ============================================================ STAGE 1: convert
if (Stage-Due "convert") {
  Write-Banner "STAGE 1  convert  (test split only)"
  "  The train split is skipped on purpose: a test-only run never reads it, and"
  "  converting it would cost ~440 MB of parquet and ~20 min for nothing."
  Assert-FreeDisk 900 "convert"
  $preConvert = @{}
  foreach ($cn in @("test_source1", "test_source2", "test_source3")) {
    $preConvert[(Join-Path $Work "data\$cn.parquet")] = (Test-Path (Join-Path $Work "data\$cn.parquet"))
  }
  Invoke-Stage -Name "convert" -ArgList @("convert.py", $Dataset, (Join-Path $Work "data"))
  Format-Budget "after-convert" ("data/ = {0} MB" -f (Get-DirMB (Join-Path $Work "data")))
  # Row counts are the measured truth of this dataset; a short file means a truncated read.
  Write-Banner "ARTIFACT CHECK after convert"
  Assert-Artifacts -Name "convert" -PreExisted $preConvert -Paths @(
    (Join-Path $Work "data\test_source1.parquet"),
    (Join-Path $Work "data\test_source2.parquet"),
    (Join-Path $Work "data\test_source3.parquet")
  ) -RowCounts @{
    (Join-Path $Work "data\test_source1.parquet") = 1732544
    (Join-Path $Work "data\test_source2.parquet") = 4887273
    (Join-Path $Work "data\test_source3.parquet") = 5082316
  }
}

# ============================================================ STAGE 2: prep
if (Stage-Due "prep") {
  Write-Banner "STAGE 2  prep  (test split only, one file at a time)"
  "  Streaming: one batch at a time straight into a ParquetWriter. Peak RAM is a"
  "  function of PREP_CHUNK, not of file size (measured 168 MB flat on test_source1)."
  Assert-FreeDisk 1600 "prep (data 522 MB held + ~1030 MB of norm output)"
  $preNorm = @{}
  foreach ($cn in @("test_source1", "test_source2", "test_source3")) {
    $preNorm[(Join-Path $Work "${cn}_norm.parquet")] = (Test-Path (Join-Path $Work "${cn}_norm.parquet"))
  }
  Invoke-Stage -Name "prep" -ArgList @("prep.py", (Join-Path $Work "data"), $Work, "test_source1", "test_source2", "test_source3")
  Format-Budget "after-prep" ("work/ = {0} MB" -f (Get-DirMB $Work))

  # This is the guard that was missing when prep died silently: the stage exited and
  # wrote nothing, which looked the same as success from the outside.
  Write-Banner "ARTIFACT CHECK after prep"
  Assert-Artifacts -Name "prep" -PreExisted $preNorm -Paths @(
    (Join-Path $Work "test_source1_norm.parquet"),
    (Join-Path $Work "test_source2_norm.parquet"),
    (Join-Path $Work "test_source3_norm.parquet")
  ) -RowCounts @{
    (Join-Path $Work "test_source1_norm.parquet") = 1732544
    (Join-Path $Work "test_source2_norm.parquet") = 4887273
    (Join-Path $Work "test_source3_norm.parquet") = 5082316
  }

  if (-not $KeepIntermediates) {
    Write-Banner "RECLAIM after prep:  work/data/*.parquet"
    "  Nothing downstream reads work/data. run_blocking builds test_s1/test_q from"
    "  the *_norm.parquet files, and nothing after run_blocking reads *_norm at all."
    $f0 = Get-FreeDiskMB
    Get-ChildItem (Join-Path $Work "data") -Filter *.parquet -File -ErrorAction SilentlyContinue |
      ForEach-Object { Remove-WorkFile $_.FullName }
    "  reclaimed {0} MB" -f ($f0 - (Get-FreeDiskMB))
  }
  Format-Budget "after-reclaim" "norm/ only"
}

# ============================================================ STAGE 3: run_blocking
if (Stage-Due "blocking") {
  Write-Banner "STAGE 3  run_blocking  test"
  "  Already resumable upstream: it skips any test_cand_{country}.parquet that exists."
  # norm 1030 still on disk + test_s1 149 + test_q 894 + cand 421 + the concatenated
  # test_cand.parquet 421 + _tmp_q_<largest country> ~190 = 3105 MB
  Assert-FreeDisk 3400 "run_blocking"
  Invoke-Stage -Name "run_blocking" -ArgList @("run_blocking.py", "test", $Work)
  Format-Budget "after-blocking" ("work/ = {0} MB" -f (Get-DirMB $Work))

  # run_blocking is per-country resumable, so assert that every country it discovered
  # in test_s1 actually produced a candidate file - a country that silently produced
  # nothing would just be missing rows from the final submission.
  Write-Banner "ARTIFACT CHECK after run_blocking"
  $cn = @(Get-ChildItem $Work -Filter "test_cand_*.parquet" -File -ErrorAction SilentlyContinue)
  "  candidate files: $($cn.Count)  ->  $(@($cn | ForEach-Object { $_.BaseName }) -join ', ')"
  $miss = @()
  foreach ($c in (Get-S1Counts)) {
    if (-not (Test-Path (Join-Path $Work "test_cand_$($c.Name).parquet"))) { $miss += $c.Name }
  }
  if ($miss.Count -gt 0) {
    "  [HARD FAILURE] run_blocking reported success but no candidate file for: $($miss -join ', ')"
    "  Those records would be silently dropped from the submission."
    throw "run_blocking incomplete for: $($miss -join ', ')"
  }
  "  [ok] every country has a test_cand_<country>.parquet"

  if (-not $KeepIntermediates) {
    Write-Banner "RECLAIM after run_blocking"
    "  test_cand.parquet is the concatenation; build_features reads the per-country"
    "  files, so the concatenation is dead weight.  *_norm.parquet is likewise dead:"
    "  test_s1.parquet and test_q.parquet are already built from it."
    $f0 = Get-FreeDiskMB
    Remove-WorkFile (Join-Path $Work "test_cand.parquet")
    Get-ChildItem $Work -Filter "*_norm.parquet" -File -ErrorAction SilentlyContinue |
      ForEach-Object { Remove-WorkFile $_.FullName }
    Get-ChildItem $Work -Filter "_tmp_q_*.parquet" -File -ErrorAction SilentlyContinue |
      ForEach-Object { Remove-WorkFile $_.FullName }
    "  reclaimed {0} MB" -f ($f0 - (Get-FreeDiskMB))
  }
  Format-Budget "after-reclaim" "test_s1 + test_q + per-country cand only"
}


# ============================================================ STAGE 4: per country
if (Stage-Due "features") {
  $s1 = Get-S1Counts
  if ($Countries) {
    $want = @($Countries.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $s1 = @($s1 | Where-Object { $want -contains $_.Name })
    if ($s1.Count -eq 0) { throw "-Countries '$Countries' matched none of the countries in test_s1" }
  }
  Write-Banner "STAGE 4  features + scoring, ONE COUNTRY AT A TIME"
  "  Order is SMALLEST feature parquet first, which is the opposite of largest-S1."
  "  That is deliberate: the on-disk base SHRINKS as countries finish (each reclaim"
  "  drops a candidate file and leaves only a small best_*.parquet), so running the"
  "  biggest one LAST is what minimises the peak."
  $s1 | ForEach-Object { "    {0,-10} S1={1,9}  pairs={2,10}  feat~{3,6} MB" -f $_.Name, $_.Count, $_.Pairs, [math]::Round($(if ($_.Pairs -gt 0) { $_.Pairs } else { $_.Count * 30.5 }) * $script:Disk.bytes_per_pair / 1MB, 0) }
  if ($MaxCountries -gt 0) { "  -MaxCountries $MaxCountries : at most $MaxCountries country/countries this invocation" }

  # work/data is dead by now and is 522 MB - on this disk that is the difference between
  # the features stage fitting and not, so reclaim it here too, not only after prep.
  Remove-StaleDataDir | Out-Null
  Format-Budget "after-reclaim" ("work/ = {0} MB (data/ removed)" -f (Get-DirMB $Work))

  $didThisRun = 0
  foreach ($c in $s1) {
    $n    = $c.Name
    $tag  = ($n -replace '[^A-Za-z0-9]', '_')
    $done = Join-Path $Work "feat\.done_test_$n"
    $best = Join-Path $Work "best_$n.parquet"

    if ((Test-Path $done) -and (Test-Path $best)) {
      Write-Banner "COUNTRY $n  already complete (marker + best_$n.parquet) - skipping"
      continue
    }
    if ($MaxCountries -gt 0 -and $didThisRun -ge $MaxCountries) {
      Write-Banner "COUNTRY $n  DEFERRED (-MaxCountries $MaxCountries reached)"
      "  Re-run the same command to continue with the next country. Everything already"
      "  finished is skipped via its .done_test_<country> marker, so this is safe."
      break
    }
    $didThisRun++
    if ((Test-Path $best) -and -not (Test-Path $done)) {
      "  note: best_$n.parquet exists from an earlier run but the feature marker does"
      "  not; make_submission will reuse the existing best file, which is safe."
    }

    # ---- features for this country
    $mdl    = $script:Disk
    $pairs  = if ($c.Pairs -gt 0) { $c.Pairs } else { [math]::Round($c.Count * $mdl.pairs_per_s1) }
    $featMB = [math]::Round($pairs * $mdl.bytes_per_pair / 1MB, 0)
    $predMB = [math]::Round($pairs * $mdl.pred_per_pair / 1MB, 0)
    $bestMB = [math]::Round($c.Count * $mdl.queries_per_s1 * $mdl.best_per_query / 1MB, 0)
    # Measure what work/ ACTUALLY holds right now rather than assuming the base from
    # the model: after N-1 countries the base includes their surviving best_*.parquet
    # and excludes their (already deleted) candidate files, so it is not a constant.
    $baseNow = Get-DirMB $Work
    $needFeat = [math]::Ceiling($baseNow + $featMB)
    Assert-FreeDisk $needFeat "features for $n (work/ $baseNow MB now + projected $featMB MB of feature parquet)"
    "  disk guard: have {0} MB, need {1} MB (work/ {2} + feat {3}), slack {4} MB" -f `
        (Get-FreeDiskMB), $needFeat, $baseNow, $featMB, ((Get-FreeDiskMB) - $needFeat)

    Invoke-Stage -Name "feat_$tag" -ArgList @("build_features.py", "test", $Work) -ExtraEnv @("COUNTRIES=$n")
    Format-Budget "after-features" ("{0}: feat/ = {1} MB" -f $n, (Get-DirMB (Join-Path $Work "feat")))

    # ---- score this country (stage 1 + stage 2, writing pred_<c> and best_<c>)
    $baseNow2 = Get-DirMB $Work
    $needScore = [math]::Ceiling($baseNow2 + $predMB + $bestMB)
    Assert-FreeDisk $needScore "scoring for $n (work/ $baseNow2 MB now + pred $predMB MB + best $bestMB MB)"
    Invoke-Stage -Name "score_$tag" -ArgList @("make_submission.py", $Work, $Out) -ExtraEnv @("COUNTRIES=$n")
    Format-Budget "after-score" ("best_{0}.parquet = {1}" -f $n, (Test-Path $best))

    # ---- reclaim: this country's feature parquet has been consumed
    if (-not $KeepIntermediates) {
      Write-Banner "RECLAIM after scoring $n"
      $f0 = Get-FreeDiskMB
      Get-ChildItem (Join-Path $Work "feat") -Filter "test_${n}_part*.parquet" -File -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-WorkFile $_.FullName -Quiet }
      Remove-WorkFile (Join-Path $Work "pred_$n.parquet") -Quiet | Out-Null
      Remove-WorkFile (Join-Path $Work "test_cand_$n.parquet") -Quiet | Out-Null
      "  freed {0} MB;  free disk {1} -> {2} MB" -f ($f0 - (Get-FreeDiskMB)), $f0, (Get-FreeDiskMB)
    }
    Format-Budget "after-reclaim" ("{0} done; feat/ = {1} MB" -f $n, (Get-DirMB (Join-Path $Work "feat")))
  }
}

# ============================================================ STAGE 5: finalize
if (Stage-Due "finalize") {
  Write-Banner "STAGE 5  make_submission FINALIZE  (join per-country results, write the 2 TSVs)"
  $nBest = @(Get-ChildItem $Work -Filter "best_*.parquet" -File -ErrorAction SilentlyContinue).Count
  "  found $nBest per-country best_*.parquet file(s)"
  if ($nBest -eq 0) { throw "FINALIZE needs at least one best_<country>.parquet - run the features stage first" }
  Assert-FreeDisk 500 "finalize"
  # COUNTRIES= is cleared as well as FINALIZE=1: the per-country loop leaves
  # COUNTRIES set to the last country, and make_submission.py refuses to run with
  # both COUNTRIES and FINALIZE set.
  Invoke-Stage -Name "finalize" -ArgList @("make_submission.py", $Work, $Out) -ExtraEnv @("FINALIZE=1", "COUNTRIES=")
  Format-Budget "after-finalize" ""
  Get-ChildItem $Out -Filter *.tsv -File | ForEach-Object {
    "  {0,-24} {1,6} MB  {2} data rows" -f $_.Name, [math]::Round($_.Length / 1MB, 1), `
        ((Get-Content $_.FullName | Measure-Object -Line).Lines - 1)
  }
}

# ============================================================ STAGE 6: validate
if (Stage-Due "validate") {
  Write-Banner "STAGE 6  POSTFLIGHT validate_submission.py"
  "  --check-ids is deliberately NOT passed: it loads every Source-2/3 id into memory"
  "  (a few GB) and this box has ~1 GB free. It is a diagnostic, not a submission gate."
  $vout = & $Py $Validator --matching (Join-Path $Out "matching_results.tsv") `
                         --candidate (Join-Path $Out "candidate_pairs.tsv") `
                         --test-dir (Join-Path $Dataset "test") 2>&1
  $vcode = $LASTEXITCODE
  $vout | ForEach-Object { "    $_" }
  Write-Banner ("VALIDATOR exit={0}   freeDisk={1} MB   freeRAM={2} MB" -f $vcode, (Get-FreeDiskMB), (Get-FreeRAMMB))
  if ($vcode -ne 0) { throw "validate_submission.py FAILED (exit $vcode) - the output files are not submittable" }
  "  FORMAT CHECK PASSED."

  # Format alone is not enough - the official validator passes a wholly empty
  # submission, so the run must also prove the files actually carry ids.
  Write-Banner "STAGE 6b  non-empty check  (format-valid but empty files must still fail)"
  $nout = & $Py (Join-Path $Src "check_nonempty.py") $Out 2>&1
  $ncode = $LASTEXITCODE
  $nout | ForEach-Object { "    $_" }
  if ($ncode -ne 0) { throw "check_nonempty.py FAILED - the files are well-formed but carry no ids, so they would score ~0" }
  "  NON-EMPTY CHECK PASSED - the two output files are submittable and scoreable."
}

# ---- where did we stop, and what is the next command?
$lastRun = @($StageNames | Where-Object { Stage-Due $_ } | Select-Object -Last 1)
$nextStage = $null
foreach ($sn in $StageNames) { if ($Stages[$sn] -gt $StopAt) { $nextStage = $sn; break } }
Write-Banner ("STOPPED after stage '{0}'   (ran -From {1} -StopAfter {2})" -f ($lastRun -join ","), $From, $StopAfter)
"  work/ now holds {0} MB;  freeDisk={1} MB;  freeRAM={2} MB" -f (Get-DirMB $Work), (Get-FreeDiskMB), (Get-FreeRAMMB)
if (Stage-Due "features") {
  $rem = @(Get-ChildItem (Join-Path $Work "feat") -Filter ".done_test_*" -File -ErrorAction SilentlyContinue).Count
  "  countries with a .done_test_<c> marker: {0} of 3" -f $rem
}
if ($nextStage) {
  ""
  "  NEXT COMMAND:"
  "    powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -From $nextStage"
  if ($nextStage -eq "features") { "      (add -MaxCountries 1 to do one country at a time)" }
} else {
  "  That was the last stage. The submission is in $Out"
}


