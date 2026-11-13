[CmdletBinding()]
param(
    [switch]$RemoveBuild,
    [switch]$RemoveDist,
    [switch]$RemoveAppliedPatchNotes
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$GeneratedDirectories = @(
    ".hypothesis",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pyright",
    ".tox",
    ".nox",
    "pulsarlab.egg-info"
)

# Remove __pycache__ directories anywhere in the project tree.
Get-ChildItem -Path $Root -Directory -Recurse -Force -Filter "__pycache__" |
    Sort-Object { $_.FullName.Length } -Descending |
    ForEach-Object {
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
        Write-Host "Eliminado: $($_.FullName.Substring($Root.Length + 1))"
    }

foreach ($RelativePath in $GeneratedDirectories) {
    $Target = Join-Path $Root $RelativePath
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
        Write-Host "Eliminado: $RelativePath"
    }
}

if ($RemoveBuild) {
    $Target = Join-Path $Root "build"
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
        Write-Host "Eliminado: build"
    }
}

if ($RemoveDist) {
    $Target = Join-Path $Root "dist"
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
        Write-Host "Eliminado: dist (artefactos de distribución)"
    }
}

if ($RemoveAppliedPatchNotes) {
    $ObsoleteNotes = @(
        "INSTRUCCIONES_APLICAR_ACTUALIZACION.txt",
        "INSTRUCCIONES_APLICAR_V3.txt",
        "NOTAS_CORRECCION_V2.md",
        "NOTAS_CORRECCION_RUFF_V3.md"
    )
    foreach ($RelativePath in $ObsoleteNotes) {
        $Target = Join-Path $Root $RelativePath
        if (Test-Path -LiteralPath $Target) {
            Remove-Item -LiteralPath $Target -Force
            Write-Host "Eliminado: $RelativePath"
        }
    }
}

Write-Host ""
Write-Host "Limpieza local terminada. No se modificó código fuente ni se tocaron datos del usuario."
if (-not $RemoveDist) {
    Write-Host "Se conservó dist/ para proteger instaladores y ejecutables existentes."
}
