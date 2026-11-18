<#
.SYNOPSIS
    Builds NotEnoughWaypoints.pak and NotEnoughWaypointsUninstaller.pak (and a Nexus-ready zip
    of each) with LSLib's Divine.exe.

.DESCRIPTION
    1. Validates both meta.lsx files: the right folders, and the same version.
    2. Checks waypoints.json and that the generated mod files are up to date
       (tools/build_waypoints.py --check; with the game cache it also checks every
       waypoint against the game's navigation grid), then compiles the story of both mods
       together with the game's (tools/check_story.py; needs the game and LSLib's ExportTool,
       and is skipped with a note without them).
    3. For each mod, stages ONLY its folder under Mods/ (and, for the mod, Localization/) into
       build/pak (README, tools and caches never end up inside a pak), converts the level and
       name files from .lsx to .lsf and the names from .xml to .loca, and packs it with Divine.exe.
    4. Lists each package to verify that the expected files are inside, nothing else is, and
       nothing in it would replace one of the game's own files.
    5. Writes dist/<mod>.pak and dist/<mod>-<version>.zip for both (the zips, with info.json
       inside, are what you upload to Nexus; BG3 Mod Manager and Vortex both import them).

.PARAMETER DivinePath
    Path to Divine.exe. Auto-detected from PATH, ./tools, LSLib/ExportTool folders and Vortex.

.PARAMETER OutputDir
    Output folder (default: ./dist).

.PARAMETER Install
    Also copy NotEnoughWaypoints.pak into %LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods.
    You still need to enable it in BG3 Mod Manager / Vortex.

.PARAMETER InstallUninstaller
    Also copy NotEnoughWaypointsUninstaller.pak there, to test taking the mod out of a save.

.PARAMETER SkipDataCheck
    Do not run tools/build_waypoints.py --check and tools/check_story.py before packing.

.EXAMPLE
    .\pack.ps1
    .\pack.ps1 -DivinePath "C:\Tools\ExportTool\tools\Divine.exe" -Install
#>
[CmdletBinding()]
param(
    [string]$DivinePath = "",
    [string]$OutputDir = "",
    [switch]$Install,
    [switch]$InstallUninstaller,
    [switch]$SkipDataCheck
)

$ErrorActionPreference = "Stop"
$ModName = "NotEnoughWaypoints"
$UninstallerName = "NotEnoughWaypointsUninstaller"
$Root = $PSScriptRoot
$LocaDir = Join-Path $Root "Localization"
if (-not $OutputDir) { $OutputDir = Join-Path $Root "dist" }
$BuildDir = Join-Path $Root "build"

function Fail([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Read-Meta([string]$Name) {
    $path = Join-Path $Root "Mods\$Name\meta.lsx"
    if (-not (Test-Path $path)) { Fail "meta.lsx not found at $path" }
    try { [xml]$meta = Get-Content -Raw -Encoding UTF8 $path } catch { Fail "$Name meta.lsx is not valid XML: $_" }
    $info = @{}
    foreach ($attr in $meta.save.region.node.children.node | Where-Object { $_.id -eq "ModuleInfo" } | ForEach-Object { $_.attribute }) {
        $info[$attr.id] = $attr.value
    }
    if ($info["Folder"] -ne $Name) { Fail "$Name meta.lsx Folder is '$($info["Folder"])', expected '$Name'" }
    return $info
}

Write-Host "== Not Enough Waypoints packager ==" -ForegroundColor Cyan

# ----------------------------------------------------------------- 1. validate
$info = Read-Meta $ModName
$uninstallerInfo = Read-Meta $UninstallerName
if ($info["Version64"] -ne $uninstallerInfo["Version64"]) {
    Fail "the mod and the uninstaller have different versions in meta.lsx: they are released together"
}
[long]$v64 = $info["Version64"]
$major = $v64 -shr 55
$minor = ($v64 -shr 47) -band 0xFF
$revision = ($v64 -shr 31) -band 0xFFFF
$build = $v64 -band 0x7FFFFFFF
$Version = "$major.$minor.$revision.$build"
Write-Host "Mod: $($info["Name"]) v$Version  UUID $($info["UUID"])"
Write-Host "     $($uninstallerInfo["Name"]) v$Version  UUID $($uninstallerInfo["UUID"])"

$Waypoints = (Get-Content -Raw -Encoding UTF8 (Join-Path $Root "waypoints.json") | ConvertFrom-Json).waypoints
if (-not $Waypoints) { Fail "waypoints.json has no waypoints" }

# ------------------------------------------------------- 2. checks (optional)
if (-not $SkipDataCheck) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
    if ($py) {
        Write-Host "Checking the waypoints..." -ForegroundColor DarkGray
        & $py.Source (Join-Path $Root "tools\build_waypoints.py") --check
        if ($LASTEXITCODE -ne 0) { Fail "Waypoint check failed (see above). Fix it or pass -SkipDataCheck." }
        Write-Host "Compiling the story with the game's..." -ForegroundColor DarkGray
        $storyArgs = @()
        if ($DivinePath) { $storyArgs += "--divine", $DivinePath }
        & $py.Source (Join-Path $Root "tools\check_story.py") @storyArgs
        if ($LASTEXITCODE -eq 1) { Fail "The story check found problems (see above). Fix them or pass -SkipDataCheck." }
        if ($LASTEXITCODE -ne 0) { Write-Host "The story was not compiled with the game's (see above)." -ForegroundColor Yellow }
    } else {
        Write-Host "Skipping the checks (needs Python)." -ForegroundColor DarkGray
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

# ------------------------------------------------- 4. stage, pack and verify
function New-ModPackage([string]$Name, [hashtable]$Meta, [string[]]$Required, [bool]$WithNames) {
    $stage = Join-Path $BuildDir "pak\$Name"
    if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
    $stageMod = Join-Path $stage "Mods\$Name"
    New-Item -ItemType Directory -Force -Path (Split-Path $stageMod) | Out-Null
    Copy-Item -Recurse -Path (Join-Path $Root "Mods\$Name") -Destination $stageMod

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
    if ($WithNames) {
        $stageLoca = Join-Path $stage "Localization"
        foreach ($xml in (Get-ChildItem -LiteralPath $LocaDir -Recurse -Filter *.xml)) {
            $rel = $xml.FullName.Substring($LocaDir.Length + 1)
            $loca = [System.IO.Path]::ChangeExtension((Join-Path $stageLoca $rel), ".loca")
            New-Item -ItemType Directory -Force -Path (Split-Path $loca) | Out-Null
            & $Divine -g bg3 -a convert-loca -s $xml.FullName -d $loca -l warn
            if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $loca)) { Fail "Could not convert $rel to .loca" }
        }
    }

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $pak = Join-Path $OutputDir "$Name.pak"
    if (Test-Path $pak) { Remove-Item -Force $pak }
    Write-Host "Packing $Name..." -ForegroundColor Cyan
    & $Divine -g bg3 -a create-package -s $stage -d $pak -l warn
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $pak)) { Fail "Divine failed with exit code $LASTEXITCODE" }

    $listing = & $Divine -g bg3 -a list-package -s $pak -l warn | ForEach-Object { ($_ -split "`t")[0] } | Where-Object { $_ }
    foreach ($file in $Required) {
        if (-not ($listing -contains $file)) { Fail "$Name.pak is missing $file" }
    }
    $stray = $listing | Where-Object { $_ -notmatch "^Mods/$Name/" -and $_ -notmatch "^Localization/[^/]+/$Name\.loca$" }
    if ($stray) { Fail "$Name.pak contains files outside Mods/$Name/ and Localization/<Language>/$Name.loca: $($stray -join ', ')" }
    $sources = $listing | Where-Object { ($_ -match "\.lsx$" -and $_ -notmatch "/meta\.lsx$") -or $_ -match "\.xml$" }
    if ($sources) { Fail "$Name.pak contains unconverted sources: $($sources -join ', ')" }
    $extra = $listing | Where-Object { $_ -notin $Required }
    if ($extra) { Fail "$Name.pak contains files that waypoints.json and the mod's layout do not explain: $($extra -join ', ')" }
    Write-Host "Package verified ($($listing.Count) files)." -ForegroundColor Green

    # info.json for the mod managers, and the zip with both
    $zipDir = Join-Path $BuildDir "zip\$Name"
    New-Item -ItemType Directory -Force -Path $zipDir | Out-Null
    $md5 = (Get-FileHash -Algorithm MD5 $pak).Hash.ToLowerInvariant()
    $infoJson = [ordered]@{
        Mods = @([ordered]@{
            Author = $Meta["Author"]
            Name = $Meta["Name"]
            Folder = $Meta["Folder"]
            Version = "$v64"
            Description = $Meta["Description"]
            UUID = $Meta["UUID"]
            Created = (Get-Date).ToString("o")
            Dependencies = @()
            Group = $Meta["UUID"]
        })
        MD5 = $md5
    }
    $infoPath = Join-Path $zipDir "info.json"
    [System.IO.File]::WriteAllText($infoPath, ($infoJson | ConvertTo-Json -Depth 5 -Compress), (New-Object System.Text.UTF8Encoding($false)))
    $zip = Join-Path $OutputDir "$Name-$Version.zip"
    if (Test-Path $zip) { Remove-Item -Force $zip }
    Compress-Archive -Path $pak, $infoPath -DestinationPath $zip
    $size = [Math]::Round((Get-Item $pak).Length / 1KB, 1)
    Write-Host "Built $pak ($size KB) and $zip" -ForegroundColor Green
}

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
    if ($wp.rock) {   # a rune on a wall has no rock
        $required += "Mods/$ModName/Levels/$($wp.level)/Scenery/$($wp.rock.guid).lsf"
    }
}
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-ModPackage $ModName $info $required $true

# The uninstaller is its story and nothing else: no objects, no names.
New-ModPackage $UninstallerName $uninstallerInfo @(
    "Mods/$UninstallerName/meta.lsx",
    "Mods/$UninstallerName/Story/RawFiles/Goals/$UninstallerName.txt"
) $false

Remove-Item -Recurse -Force $BuildDir
$stale = Join-Path $OutputDir "info.json"   # written next to the pak by versions before 1.2
if (Test-Path $stale) { Remove-Item -Force $stale }
Write-Host ""
Write-Host "Upload both zips in $OutputDir to Nexus: the mod as the main file, the uninstaller as an optional file." -ForegroundColor Green

# ----------------------------------------------------------------- 5. install
$modsFolder = Join-Path $env:LOCALAPPDATA "Larian Studios\Baldur's Gate 3\Mods"
foreach ($pair in @(@($Install, $ModName), @($InstallUninstaller, $UninstallerName))) {
    if ($pair[0]) {
        New-Item -ItemType Directory -Force -Path $modsFolder | Out-Null
        Copy-Item -Force (Join-Path $OutputDir "$($pair[1]).pak") $modsFolder
        Write-Host "Copied $($pair[1]).pak to $modsFolder - enable it in BG3 Mod Manager or Vortex." -ForegroundColor Green
    }
}
