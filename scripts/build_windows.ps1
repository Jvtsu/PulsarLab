[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipPortable,
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "Este script debe ejecutarse en Windows. PyInstaller genera el binario para el sistema donde se ejecuta."
}

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$VersionMatch = Select-String -Path (Join-Path $Root "pyproject.toml") -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $VersionMatch) { throw "No se pudo leer la versión desde pyproject.toml." }
$Version = $VersionMatch.Matches[0].Groups[1].Value

function Find-Python {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & $PyLauncher.Source -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @($PyLauncher.Source, "-3.11") }
        & $PyLauncher.Source -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @($PyLauncher.Source, "-3") }
    }

    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) { return @($Candidate) }
    }

    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) { return @($PythonCommand.Source) }
    return $null
}

function Install-PythonIfMissing {
    $PythonCommand = Find-Python
    if ($PythonCommand) { return $PythonCommand }

    $Winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $Winget) {
        throw "No se encontró Python ni winget. Instala Python 3.11 de 64 bits y vuelve a ejecutar BUILD_EXE_WINDOWS.bat."
    }

    Write-Host "Python 3.11 no está instalado. Se instalará automáticamente..."
    & $Winget.Source install --id Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "No fue posible instalar Python 3.11." }

    $PythonCommand = Find-Python
    if (-not $PythonCommand) { throw "Python se instaló, pero no pudo localizarse. Reinicia Windows y ejecuta nuevamente el archivo BAT." }
    return $PythonCommand
}

function Find-InnoSetup {
    $Candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe"
    )
    return $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

function Install-InnoSetupIfMissing {
    $ISCC = Find-InnoSetup
    if ($ISCC) { return $ISCC }

    $Winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $Winget) { return $null }

    Write-Host "Inno Setup no está instalado. Se instalará para crear PulsarLab-Setup.exe..."
    & $Winget.Source install --id JRSoftware.InnoSetup.7 -e --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { return $null }
    return Find-InnoSetup
}

$Venv = Join-Path $Root ".venv-build"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, $Venv
}

if (-not (Test-Path $VenvPython)) {
    $PythonCommand = Install-PythonIfMissing
    $PythonExe = $PythonCommand[0]
    $PythonArgs = @()
    if ($PythonCommand.Count -gt 1) { $PythonArgs = $PythonCommand[1..($PythonCommand.Count - 1)] }
    & $PythonExe @PythonArgs -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "No fue posible crear el entorno de compilación." }
}

& $VenvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "Falló la preparación de pip." }
& $VenvPython -m pip install -r requirements-win.txt "pyinstaller>=6.10,<7"
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de dependencias." }

if (-not $SkipTests) {
    & $VenvPython -m pip install "pytest>=8"
    & $VenvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Las pruebas fallaron. No se generará un instalador defectuoso." }
}

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist

& $PyInstaller --noconfirm --clean packaging\windows\PulsarLab-folder.spec
if ($LASTEXITCODE -ne 0) { throw "Falló la compilación de la carpeta ejecutable." }

& (Join-Path $Root "dist\PulsarLab\PulsarLab.exe") --smoke-test
if ($LASTEXITCODE -ne 0) { throw "El ejecutable se creó, pero falló su prueba de apertura." }

$PortableZip = Join-Path $Root "dist\PulsarLab-$Version-Windows-x64.zip"
Compress-Archive -Path (Join-Path $Root "dist\PulsarLab\*") -DestinationPath $PortableZip -Force

if (-not $SkipPortable) {
    & $PyInstaller --noconfirm --clean packaging\windows\PulsarLab-portable.spec
    if ($LASTEXITCODE -ne 0) { throw "Falló la compilación del ejecutable portátil." }
    & (Join-Path $Root "dist\PulsarLab-Portable.exe") --smoke-test
    if ($LASTEXITCODE -ne 0) { throw "El ejecutable portátil se creó, pero falló su prueba de apertura." }
}

if (-not $SkipInstaller) {
    $ISCC = Install-InnoSetupIfMissing
    if (-not $ISCC) {
        Write-Warning "No fue posible instalar Inno Setup. Se creó el .exe y el ZIP, pero no PulsarLab-Setup.exe."
    } else {
        & $ISCC "/DMyAppVersion=$Version" "packaging\windows\PulsarLab.iss"
        if ($LASTEXITCODE -ne 0) { throw "Falló la creación del instalador Inno Setup." }
    }
}

$HashFiles = Get-ChildItem -Path dist -Recurse -File | Where-Object {
    $_.Extension -in ".exe", ".zip"
}
$HashLines = foreach ($File in $HashFiles) {
    $Hash = Get-FileHash -Algorithm SHA256 $File.FullName
    "{0}  {1}" -f $Hash.Hash.ToLowerInvariant(), $File.FullName.Substring($Root.Length + 1)
}
$HashLines | Set-Content -Encoding ASCII (Join-Path $Root "dist\SHA256SUMS-Windows.txt")

Write-Host ""
Write-Host "===================================================="
Write-Host " PulsarLab para Windows quedó listo"
Write-Host "===================================================="
Write-Host "Instalador recomendado: dist\installer\PulsarLab-Setup-$Version-Windows-x64.exe"
Write-Host "Ejecutable portátil:   dist\PulsarLab-Portable.exe"
Write-Host "Carpeta portátil:      dist\PulsarLab-$Version-Windows-x64.zip"
