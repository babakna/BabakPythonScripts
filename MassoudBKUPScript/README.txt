# README
# Store the script in C:\Scripts\AutomateBackup.ps1
# Add a shortcut and for the command enter:
#   powershell.exe -ExecutionPolicy Bypass -File "C:\Path\To\Your\AutomateBackup.ps1"
# Add a proper name an Icon
# Update the $sourcePaths and $usbDriveLetter variables in the script
# Test It
# Need to give it admin privilege. Run the following once
# open powershell as admin and run the following
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Afterwards, you can run the script in powershell without admin privilege