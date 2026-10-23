param([switch]$Offline)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if ($pythonCommand) {
    $analysisPython = $pythonCommand.Source
} elseif (Test-Path -LiteralPath $bundledPython) {
    $analysisPython = $bundledPython
} else {
    throw 'No se encuentra Python. Instala Python 3.10 o superior y vuelve a ejecutar este archivo.'
}
$analysisArguments = @('-m', 'racing_analysis', 'demo')
if ($Offline) { $analysisArguments += '--offline' }
& $analysisPython @analysisArguments
if ($LASTEXITCODE -ne 0) { throw 'No se ha podido generar el informe. Revisa el mensaje anterior.' }
Start-Process -FilePath (Join-Path $PSScriptRoot 'output\informe.html')
