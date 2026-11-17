<#
.SYNOPSIS
    Builds NotEnoughWaypoints.pak (and a Nexus-ready zip) with LSLib's Divine.exe.

.DESCRIPTION
    1. Validates meta.lsx.
    2. Checks waypoints.json and that the generated mod files are up to date
       (tools/build_waypoints.py --check; with the game cache it also checks every
       waypoint against the game's navigation grid).
    3. Stages ONLY Mods/NotEnoughWaypoints and Localization/English into build/pak
       (README, tools and caches never end up inside the pak), converts the level and
       name files from .lsx to .lsf and the English names from .xml to .loca, and
       packs it with Divine.exe.
    4. Lists the package to verify the expected files are inside, and that nothing
       in it would replace one of the game's own files.
    5. Writes dist/NotEnoughWaypoints.pak, dist/info.json and dist/NotEnoughWaypoints-<version>.zip
       (the zip is what you upload to Nexus; BG3 Mod Manager and Vortex both import it).

.PARAMETER DivinePath
    Path to Divine.exe. Auto-detected from PATH, ./tools, LSLib/ExportTool folders and Vortex.

.PARAMETER OutputDir
    Output folder (default: ./dist).

.PARAMETER Install
    Also copy the .pak into %LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods.
    You still need to enable it in BG3 Mod Manager / Vortex.

.PARAMETER SkipDataCheck
    Do not run tools/build_waypoints.py --check before packing.

.EXAMPLE
    .\pack.ps1
    .\pack.ps1 -DivinePath "C:\Tools\ExportTool\tools\Divine.exe" -Install
#>
[CmdletBinding()]
param(
    [string]$DivinePath = "",
    [string]$OutputDir = "",
    [switch]$Install,
    [switch]$SkipDataCheck
)

$ErrorActionPreference = "Stop"
$ModName = "NotEnoughWaypoints"
$Root = $PSScriptRoot
$ModDir = Join-Path $Root "Mods\$ModName"
$LocaDir = Join-Path $Root "Localization"
if (-not $OutputDir) { $OutputDir = Join-Path $Root "dist" }
$BuildDir = Join-Path $Root "build\pak"

function Fail([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

Write-Host "== Not Enough Waypoints packager ==" -ForegroundColor Cyan

# ----------------------------------------------------------------- 1. validate
$MetaPath = Join-Path $ModDir "meta.lsx"
if (-not (Test-Path $MetaPath)) { Fail "meta.lsx not found at $MetaPath" }
try { [xml]$meta = Get-Content -Raw -Encoding UTF8 $MetaPath } catch { Fail "meta.lsx is not valid XML: $_" }

$info = @{}
foreach ($attr in $meta.save.region.node.children.node | Where-Object { $_.id -eq "ModuleInfo" } | ForEach-Object { $_.attribute }) {
    $info[$attr.id] = $attr.value
}
if ($info["Folder"] -ne $ModName) { Fail "meta.lsx Folder is '$($info["Folder"])', expected '$ModName'" }
[long]$v64 = $info["Version64"]
$major = $v64 -shr 55
$minor = ($v64 -shr 47) -band 0xFF
$revision = ($v64 -shr 31) -band 0xFFFF
$build = $v64 -band 0x7FFFFFFF
$Version = "$major.$minor.$revision.$build"
Write-Host "Mod: $($info["Name"]) v$Version  UUID $($info["UUID"])"

$Waypoints = (Get-Content -Raw -Encoding UTF8 (Join-Path $Root "waypoints.json") | ConvertFrom-Json).waypoints
if (-not $Waypoints) { Fail "waypoints.json has no waypoints" }

# ------------------------------------------------------- 2. data check (optional)
if (-not $SkipDataCheck) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if ($py) {
        Write-Host "Checking the waypoints..." -ForegroundColor DarkGray
        & $py.Source (Join-Path $Root "tools\build_waypoints.py") --check
        if ($LASTEXITCODE -ne 0) { Fail "Waypoint check failed (see above). Fix it or pass -SkipDataCheck." }
    } else {
        Write-Host "Skipping the waypoint check (needs Python)." -ForegroundColor DarkGray
    }
}

# ------------------------------------------------------------- 3. find Divine
$candidates = @()
if ($DivinePath) { $candidates += $DivinePath }
$onPath = Get-Command Divine.exe -ErrorAction SilentlyContinue
if ($onPath) { $candidates += $onPath.Source }
$candidates += (Join-Path $Root "Divine.exe"), (Join-Path $Root "tools\Divine.exe")
$patterns = @(
    "$env:LOCALAPPDATA\Programs\LSLib\Divine.exe",
    "$env:APPDATA\Vortex\baldursgate3\mods\ExportTool*\tools\Divine.exe"
)
foreach ($drive in (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue)) {
    $r = $drive.Root
    $patterns += "${r}Tools\LSLib\Divine.exe", "${r}Tools\ExportTool*\Tools\Divine.exe",
        "${r}Modding\ExportTool*\Tools\Divine.exe", "${r}Vortex Mods\baldursgate3\ExportTool*\tools\Divine.exe"
}
foreach ($pattern in $patterns) {
    try { $candidates += (Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) } catch { }
}
$Divine = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $Divine) {
    Write-Host "Divine.exe (LSLib) was not found." -ForegroundColor Yellow
    Write-Host "Download ExportTool from https://github.com/Norbyte/lslib/releases and pass -DivinePath <path>\Tools\Divine.exe"
    exit 1
}
Write-Host "Divine: $Divine" -ForegroundColor Green

# --------------------------------------------------------------- 4. stage+pack
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
$stageMod = Join-Path $BuildDir "Mods\$ModName"
New-Item -ItemType Directory -Force -Path (Split-Path $stageMod) | Out-Null
Copy-Item -Recurse -Path $ModDir -Destination $stageMod

# The game loads the binary .lsf form of level objects and name keys, so the readable
# .lsx sources are converted here (meta.lsx stays as it is).
foreach ($lsx in (Get-ChildItem -LiteralPath $stageMod -Recurse -Filter *.lsx | Where-Object { $_.Name -ne "meta.lsx" })) {
    $lsf = [System.IO.Path]::ChangeExtension($lsx.FullName, ".lsf")
    & $Divine -g bg3 -a convert-resource -s $lsx.FullName -d $lsf -l warn
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $lsf)) { Fail "Could not convert $($lsx.Name) to .lsf" }
    Remove-Item -LiteralPath $lsx.FullName -Force
}

# Names: Localization/<Language>/NotEnoughWaypoints.xml -> .loca. The file name must stay
# unique: a mod file called english.loca would replace every English text in the game.
$stageLoca = Join-Path $BuildDir "Localization"
foreach ($xml in (Get-ChildItem -LiteralPath $LocaDir -Recurse -Filter *.xml)) {
    $rel = $xml.FullName.Substring($LocaDir.Length + 1)
    $loca = [System.IO.Path]::ChangeExtension((Join-Path $stageLoca $rel), ".loca")
    New-Item -ItemType Directory -Force -Path (Split-Path $loca) | Out-Null
    & $Divine -g bg3 -a convert-loca -s $xml.FullName -d $loca -l warn
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $loca)) { Fail "Could not convert $rel to .loca" }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$PakPath = Join-Path $OutputDir "$ModName.pak"
if (Test-Path $PakPath) { Remove-Item -Force $PakPath }

Write-Host "Packing..." -ForegroundColor Cyan
& $Divine -g bg3 -a create-package -s $BuildDir -d $PakPath -l warn
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $PakPath)) { Fail "Divine failed with exit code $LASTEXITCODE" }

# ------------------------------------------------------------------- 5. verify
$listing = & $Divine -g bg3 -a list-package -s $PakPath -l warn | ForEach-Object { ($_ -split "`t")[0] } | Where-Object { $_ }
$required = @(
    "Mods/$ModName/meta.lsx",
    "Mods/$ModName/Story/RawFiles/Goals/$ModName.txt",
    "Mods/$ModName/Localization/Waypointshrines.lsf",
    "Localization/English/$ModName.loca"
)
foreach ($wp in $Waypoints) {
    $required += "Mods/$ModName/Globals/$($wp.level)/Items/$($wp.shrine.guid).lsf",
        "Mods/$ModName/Globals/$($wp.level)/Triggers/$($wp.trigger.guid).lsf",
        "Mods/$ModName/Levels/$($wp.level)/Decals/$($wp.decal.guid).lsf"
}
foreach ($file in $required) {
    if (-not ($listing -contains $file)) { Fail "Package is missing $file" }
}
$stray = $listing | Where-Object { $_ -notmatch "^Mods/$ModName/" -and $_ -notmatch "^Localization/[^/]+/$ModName\.loca$" }
if ($stray) { Fail "Package contains files outside Mods/$ModName/ and Localization/<Language>/$ModName.loca: $($stray -join ', ')" }
$sources = $listing | Where-Object { ($_ -match "\.lsx$" -and $_ -notmatch "/meta\.lsx$") -or $_ -match "\.xml$" }
if ($sources) { Fail "Package contains unconverted sources: $($sources -join ', ')" }
$extra = $listing | Where-Object { $_ -notin $required }
if ($extra) { Fail "Package contains files that waypoints.json does not explain: $($extra -join ', ')" }
Write-Host "Package verified ($($listing.Count) files)." -ForegroundColor Green

# --------------------------------------------------------- 6. info.json + zip
$md5 = (Get-FileHash -Algorithm MD5 $PakPath).Hash.ToLowerInvariant()
$infoJson = [ordered]@{
    Mods = @([ordered]@{
        Author = $info["Author"]
        Name = $info["Name"]
        Folder = $info["Folder"]
        Version = "$v64"
        Description = $info["Description"]
        UUID = $info["UUID"]
        Created = (Get-Date).ToString("o")
        Dependencies = @()
        Group = $info["UUID"]
    })
    MD5 = $md5
}
$InfoPath = Join-Path $OutputDir "info.json"
[System.IO.File]::WriteAllText($InfoPath, ($infoJson | ConvertTo-Json -Depth 5 -Compress), (New-Object System.Text.UTF8Encoding($false)))

$ZipPath = Join-Path $OutputDir "$ModName-$Version.zip"
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path $PakPath, $InfoPath -DestinationPath $ZipPath

Remove-Item -Recurse -Force (Join-Path $Root "build")

$size = [Math]::Round((Get-Item $PakPath).Length / 1KB, 1)
Write-Host ""
Write-Host "Built $PakPath ($size KB)" -ForegroundColor Green
Write-Host "Built $ZipPath (upload this to Nexus)" -ForegroundColor Green

# ----------------------------------------------------------------- 7. install
if ($Install) {
    $modsFolder = Join-Path $env:LOCALAPPDATA "Larian Studios\Baldur's Gate 3\Mods"
    New-Item -ItemType Directory -Force -Path $modsFolder | Out-Null
    Copy-Item -Force $PakPath $modsFolder
    Write-Host "Copied to $modsFolder - enable it in BG3 Mod Manager or Vortex." -ForegroundColor Green
}
