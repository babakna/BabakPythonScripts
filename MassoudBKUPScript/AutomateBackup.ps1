# Backup script with user interface
# README
# Store the script in C:\Scripts\AutomateBackup.ps1
# Add a shortcut and for the command enter:
#   powershell.exe -ExecutionPolicy Bypass -File "C:\Path\To\Your\AutomateBackup.ps1"
# Add a proper name an Icon
# Update the $sourcePaths and $usbDriveLetter variables in the script
# Test It
# Need to give it admin privilege. Rub the follwoign once
# open pershell as admin and run the following
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser



# Add Windows Forms for GUI elements
Add-Type -AssemblyName System.Windows.Forms

# Configuration
$sourcePaths = @(
    "C:\Path\To\First\Directory",
    "C:\Path\To\Second\Directory"
    # Add more paths as needed
)
$usbDriveLetter = "E:" # Change this to your USB drive letter
$backupRoot = "$usbDriveLetter\Backups"

# Check if USB drive is connected
if (-not (Test-Path $usbDriveLetter)) {
    [System.Windows.Forms.MessageBox]::Show(
        "USB drive not found. Please connect the USB drive and try again.",
        "Backup Error",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
    exit
}

# Confirm backup
$result = [System.Windows.Forms.MessageBox]::Show(
    "Do you want to start the backup?`n`nThis will create a new backup and keep the previous one.",
    "Confirm Backup",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question
)

if ($result -eq [System.Windows.Forms.DialogResult]::No) {
    exit
}

# Create timestamp for new backup folder
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$newBackupPath = Join-Path $backupRoot $timestamp

try {
    # Create the new backup directory
    New-Item -ItemType Directory -Path $newBackupPath -Force

    # Copy each source directory to the backup location
    foreach ($sourcePath in $sourcePaths) {
        $folderName = Split-Path $sourcePath -Leaf
        $destinationPath = Join-Path $newBackupPath $folderName
        
        Copy-Item -Path $sourcePath -Destination $destinationPath -Recurse -Force
    }

    # Get all backup folders except the newest one
    $allBackups = Get-ChildItem -Path $backupRoot -Directory | 
        Sort-Object CreationTime -Descending

    # If there are more than 2 backups (current + last), delete the older ones
    if ($allBackups.Count -gt 2) {
        $allBackups | Select-Object -Skip 2 | ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force
        }
    }

    # Show success message
    [System.Windows.Forms.MessageBox]::Show(
        "Backup completed successfully!`n`nLocation: $newBackupPath",
        "Backup Complete",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    )
}
catch {
    # Show error message if something goes wrong
    [System.Windows.Forms.MessageBox]::Show(
        "An error occurred during backup:`n`n$($_.Exception.Message)",
        "Backup Error",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
}
