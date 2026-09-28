# Validates the LEET ordinal guard WITHOUT Python.
#
# WHY THIS EXISTS: the Python interpreter on this box is broken (C:\Program Files\
# Python313 has no Lib\ tree; every venv points at a deleted base). The real
# regression suite is patch_upstream/src/test_leet_ordinal_guard.py, which is the
# authoritative test because it imports the real normalize module. This harness is
# a fallback so the fix is not merely ASSERTED but actually EXERCISED.
#
# LIMITATION - stated plainly: .NET regex is not Python re. They agree on this
# simple anchored alternation, so this validates the PATTERN LOGIC and the
# token-classification decision, not Python's exact engine behaviour. The .py
# suite must still be run once Python is repaired.
#
# Replicates _name_tokens' decision exactly:
#   lower -> split on [^a-z0-9]+ -> if token has alpha AND digit
#   AND is not a whole-token ordinal -> translate(LEET)

$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)'

$LEET = @{ '0'='o'; '1'='l'; '3'='e'; '4'='a'; '5'='s'; '6'='g'; '7'='t'; '8'='b'; '@'='a'; '$'='s' }
$ORDINAL  = [regex]::new('^\d+(?:er|ere|eme|e)$')
$EN_ORD   = [regex]::new('^\d+(?:st|nd|rd|th)$')
$HOURS    = [regex]::new('^\d+hr$')
$GUARD    = [regex]::new('^(?:\d+(?:er|ere|eme|e)|\d+(?:st|nd|rd|th)|\d+hr)$')
$NONALNUM = [regex]::new('[^a-z0-9]+')

function Convert-Leet([string]$t) {
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $t.ToCharArray()) {
        $k = [string]$ch
        if ($LEET.ContainsKey($k)) { [void]$sb.Append($LEET[$k]) } else { [void]$sb.Append($ch) }
    }
    return $sb.ToString()
}

function Get-Tokens([string]$s) {
    $out = @()
    foreach ($t in ($NONALNUM.Split($s.ToLower()))) {
        if (-not $t) { continue }
        $hasAlpha = $t -match '[a-z]'
        $hasDigit = $t -match '[0-9]'
        if ($hasAlpha -and $hasDigit -and -not $GUARD.IsMatch($t)) { $t = Convert-Leet $t }
        $out += $t
    }
    return $out
}

# --- case table: token, expected, label -------------------------------------
$cases = @(
    @('3eme','3eme','GUARD ordinal'),  @('1er','1er','GUARD ordinal'),
    @('3e','3e','GUARD ordinal'),      @('2e','2e','GUARD ordinal'),
    @('1ere','1ere','GUARD ordinal'),  @('10eme','10eme','GUARD ordinal'),
    @('22e','22e','GUARD ordinal'),    @('4EME','4eme','GUARD upper'),
    @('7eme','7eme','GUARD ordinal'),

    # N1: 24-hour notation. 3,657 occurrences - the SINGLE LARGEST corruption in
    # the dataset and 3.3x the French ordinal mass. A French-only guard misses it.
    @('24hr','24hr','GUARD N1 24hr'),  @('24HR','24hr','GUARD N1 upper'),
    @('7hr','7hr','GUARD N1'),          @('12hr','12hr','GUARD N1'),

    # N2: English ordinals. 1,060 occurrences (US 679 + India 381).
    @('1st','1st','GUARD N2'),          @('2nd','2nd','GUARD N2'),
    @('3rd','3rd','GUARD N2'),          @('4th','4th','GUARD N2'),
    @('21st','21st','GUARD N2'),

    @('c1ub','club','LEET ok'),        @('mais0n','maison','LEET ok'),
    @('b3ta','beta','LEET ok'),        @('5tar','star','LEET ok'),
    @('g0ld','gold','LEET ok'),        @('n3w','new','LEET ok'),
    @('c0ff3e','coffee','LEET ok'),    @('t3am','team','LEET ok'),
    @('h0tel','hotel','LEET ok'),      @('p1zza','plzza','LEET ok (1->l)'),

    # DEAD LEET ENTRIES (pre-existing finding, NOT caused by the guard):
    # _non_alnum strips non-alphanumerics BEFORE translate() runs, so "@" and "$"
    # never reach the LEET table. Their entries are unreachable via _name_tokens.
    @('@lm','lm','DEAD @ entry'),      @('$tore','tore','DEAD $ entry'),

    # EDGE: the pattern boundary. A looser pattern such as \d+[er] would wrongly
    # guard these two and leave real leetspeak untranslated.
    @('b3er','beer','EDGE leet not ordinal'), @('p1er','pler','EDGE leet not ordinal'),
    @('3a','ea','EDGE'),               @('e3','ee','EDGE'),
    @('3','3','EDGE pure digit'),      @('abc','abc','EDGE pure alpha')
)

$pass = 0; $fail = 0
foreach ($c in $cases) {
    $tok = $c[0]; $want = $c[1]; $label = $c[2]
    $got = @(Get-Tokens $tok)[0]
    if ($got -eq $want) {
        $pass++; Write-Output ("  PASS  {0,-8} -> {1,-8}  {2}" -f $tok, $got, $label)
    } else {
        $fail++; Write-Output ("  FAIL  {0,-8} -> {1,-8}  (expected {2})  {3}" -f $tok, $got, $want, $label)
    }
}

# --- regex shape assertions ------------------------------------------------
Write-Output ''
Write-Output 'regex shape (union must match all three classes, reject the rest):'
foreach ($t in @('3eme','1er','3e','10eme','24hr','7hr','1st','2nd','3rd','4th')) {
    if ($GUARD.IsMatch($t)) { $pass++; Write-Output "  PASS  matches '$t'" }
    else { $fail++; Write-Output "  FAIL  should match '$t'" }
}
foreach ($t in @('b3er','p1er','3a','e3','abc3','3emex','x3eme','x1st','hr24','24hrs','1std')) {
    if (-not $GUARD.IsMatch($t)) { $pass++; Write-Output "  PASS  rejects '$t'" }
    else { $fail++; Write-Output "  FAIL  should reject '$t'" }
}

Write-Output ''
Write-Output 'union must agree with its three parts:'
foreach ($t in @('3eme','1er','3e','1ere','7eme','10eme','22e','24hr','7hr','12hr','1st','2nd','3rd','4th','21st')) {
    $part = $ORDINAL.IsMatch($t) -or $EN_ORD.IsMatch($t) -or $HOURS.IsMatch($t)
    if ($GUARD.IsMatch($t) -and $part) { $pass++ }
    else { $fail++; Write-Output "  FAIL  union/parts disagree on '$t'" }
}
if ($fail -eq 0) { Write-Output "  PASS  all 15 tokens agree" }

# --- mixed sentence ---------------------------------------------------------
Write-Output ''
$toks = Get-Tokens 'Boulangerie du 3eme c1ub'
if ($toks -contains '3eme' -and $toks -contains 'club' -and $toks -notcontains 'eeme') {
    $pass++; Write-Output ("  PASS  mixed sentence -> " + ($toks -join ' '))
} else {
    $fail++; Write-Output ("  FAIL  mixed sentence -> " + ($toks -join ' '))
}

# --- confirm the ORIGINAL bug still exists in the unpatched table ----------
Write-Output ''
$raw = Convert-Leet '3eme'
if ($raw -eq 'eeme') { Write-Output "  PASS  raw LEET still mangles 3eme -> eeme (guard, not the table, is the fix)" }
else { $fail++; Write-Output "  FAIL  expected raw LEET to give eeme, got $raw" }

Write-Output ''
Write-Output "TOTAL: $pass passed, $fail failed"
if ($fail -gt 0) { exit 1 }
