$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py "$ProjectDir/scripts/install_pet.py" @args
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python "$ProjectDir/scripts/install_pet.py" @args
    exit $LASTEXITCODE
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 "$ProjectDir/scripts/install_pet.py" @args
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3 first."
