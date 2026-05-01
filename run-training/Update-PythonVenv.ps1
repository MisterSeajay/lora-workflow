[CmdletBinding(SupportsShouldProcess)]
param (
)

################################################################################
# Functions
#region

function Invoke-Pip {
    [CmdletBinding(SupportsShouldProcess)]
    [OutputType([string[]])]
    param (
        [Parameter(Mandatory)]
        [string]$Command
    )

    Write-Debug "[Invoke-Pip] python -m pip $Command"

    if ($PSCmdlet.ShouldProcess($Command, "pip")) {
        $PipCommandOutput = Invoke-Expression "python -m pip $Command 2>&1"

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to run: python -m pip $Command"
            Write-Debug "pip output: $PipCommandOutput"
            return $null
        }
    } else {
        # Pretend pip ran successfully, but don't mock specific output.
        return "WhatIf output"
    }

    return $PipCommandOutput
}

function Get-PipCache {
    [CmdletBinding(SupportsShouldProcess)]
    [OutputType([string])]
    $PipConfigOutput = Invoke-Pip -Command "config get global.find-links"

    if (-not $PipConfigOutput){
        Write-Warning "No pip cache path found"
        return $null
    }
    if (-not (Test-Path $PipConfigOutput)) {
        Write-Warning "$PipConfigOutput folder is missing."
        return $null
    }

    return $PipConfigOutput
}

function is_installed {
    [CmdletBinding(SupportsShouldProcess)]
    [OutputType([boolean])]
    param (
        [Parameter(Mandatory)]
        [string]$Package
    )

    if (Invoke-Pip -Command "show $Package") {
        return $true
    }
    return $false
}

function is_correct_version {
    [CmdletBinding(SupportsShouldProcess)]
    [OutputType([boolean])]
    param (
        [Parameter(Mandatory)]
        [string]$Package,

        [Parameter(Mandatory)]
        [string]$Version
    )

    if (-not (is_installed $Package)) {
        return $false
    }

    $PipShowOutput = Invoke-Pip -Command "pip show $Package" | Select-String -Pattern "Version:"
    $InstalledVersion = (($PipShowOutput -split ":")[1] -split "\+")[0].Trim()
    Write-Debug "[is_correct_version] Installed version: $InstalledVersion"
    return ($InstalledVersion -eq $RequiredVersion)
}

function Get-MissingPackages {
    [CmdletBinding(SupportsShouldProcess)]
    [OutputType([string])]
    param (
        [Parameter(Mandatory)]
        [hashtable]$PackagesToCheck
    )
    Write-Verbose "[Get-MissingPackages] Checking installed packages..."

    $MissingPackages = @()

    foreach ($Package in $PackagesToCheck.Keys) {
        $RequiredVersion = $PackagesToCheck[$Package]
        Write-Debug "[Get-MissingPackages] Checking $Package==$RequiredVersion"

        if (-not (is_installed $Package)) {
            Write-Warning "$Package not found."
            $MissingPackages += $Package
            continue
        }

        if (is_correct_version $Package $RequiredVersion) {
            Write-Information "$Package version $InstalledVersion is correctly installed."
        } else {
            Write-Warning "$Package found, but required version is $RequiredVersion."
            $MissingPackages += $Package
        }
    }

    Write-Output $MissingPackages
}

#endregion

################################################################################
# Check Python environment

if ($env:VIRTUAL_ENV -notmatch "kohya_ss"){
    Write-Error "Please enable the virtual environment in the kohya_ss folder."
    exit 1
}

if ((python --version) -notmatch "3.11"){
    Write-Error "Please use Python 3.11."
    exit 1
}

if (-not (Invoke-Pip -Command "install --upgrade pip")) {
    Write-Error "Failed to update pip"
    exit 1
}

################################################################################
# Variables

# Package version recommendations from the bmaltais/kohya_ss repo:
$PackagesToCheck = [ordered]@{
    "torch" = "2.7.0+cu128"
    "torchvision" = "0.22.0+cu128"
    "xformers" = "0.0.30"
}

$PyTorchIndexUrl = "https://download.pytorch.org/whl/cu128"

################################################################################
# Check installed verions

$PackagesToInstall = Get-MissingPackages $PackagesToCheck

# If installation isn't needed, you can exit the script or the relevant block here
if ($PackagesToInstall.Count -lt 1) {
    Write-Information "All required packages are already installed with the correct versions. Exiting."
    exit
}

################################################################################
# Download missing packages (download ALL before installing ANY)

$DownloadDir = Get-PipCache

if($DownloadDir) {
    Write-Verbose "Downloading packages to local cache..."

    foreach ($Package in $PackagesToInstall) {
        $Command = "download $Package==$($PackagesToCheck[$Package])"
        $Command+= " --no-deps"
        $Command+= " --extra-index-url $PyTorchIndexUrl"
        $Command+= " --dest $DownloadDir"
        Invoke-Pip -Command $Command
    }

    Write-Information "Download complete. Files are in $DownloadDir."
}

################################################################################
# Install packages

$InstallationList = ""
foreach ($Package in $PackagesToInstall) {
    $InstallationList += "$Package==$($PackagesToCheck[$Package]) "
}

$InstallationList = $InstallationList.Trim()
Write-Debug $InstallationList

$Command = "install $InstallationList"

if($DownloadDir) {
    Write-Verbose "Installing packages from local cache"
    $Command+= " --no-index"
} else {
    Write-Verbose "Installing packages from $PyTorchIndexUrl"
    $Command+= " --index-url $PyTorchIndexUrl"
}

Invoke-Pip -Command $Command
Write-Information "Installation complete."