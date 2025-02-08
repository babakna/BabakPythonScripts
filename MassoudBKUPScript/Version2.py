import os
import shutil
import datetime
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Configuration
source_paths = [
    "C:/Path/To/First/Directory",
    "C:/Path/To/Second/Directory"
    # Add more paths as needed
]
usb_drive_letter = "E:/"  # Change this to your USB drive letter
backup_root = os.path.join(usb_drive_letter, "Backups")

def check_usb_drive():
    if not os.path.exists(usb_drive_letter):
        log_message("USB drive not found. Please connect the USB drive and try again.")
        return False
    return True

def log_message(message):
    display_text.config(state=tk.NORMAL)
    display_text.insert(tk.END, message + '\n')
    display_text.config(state=tk.DISABLED)
    display_text.see(tk.END)

def create_backup():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    new_backup_path = os.path.join(backup_root, timestamp)
    os.makedirs(new_backup_path, exist_ok=True)

    try:
        for source_path in source_paths:
            folder_name = os.path.basename(source_path)
            destination_path = os.path.join(new_backup_path, folder_name)
            log_message(f"Copying {source_path} to {destination_path}")
            shutil.copytree(source_path, destination_path)
        
        all_backups = sorted(Path(backup_root).iterdir(), key=os.path.getctime, reverse=True)
        if len(all_backups) > 3:
            for old_backup in all_backups[3:]:
                shutil.rmtree(old_backup)
        
        log_message("FINISHED")
        messagebox.showinfo("Backup Complete", f"Backup completed successfully!\n\nLocation: {new_backup_path}")
    except Exception as e:
        log_message(f"An error occurred during backup: {str(e)}")
        messagebox.showerror("Backup Error", f"An error occurred during backup:\n\n{str(e)}")

def on_start():
    if not check_usb_drive():
        return

    result = messagebox.askyesno("Confirm Backup", "Do you want to start the backup?\n\nThis will create a new backup and keep the previous ones.")
    if result:
        create_backup()

def on_exit():
    root.destroy()

# Setup GUI
root = tk.Tk()
root.title("Backup Script")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

start_button = tk.Button(frame, text="Start Backup", command=on_start)
start_button.pack(side=tk.LEFT, padx=5)

exit_button = tk.Button(frame, text="Exit", command=on_exit)
exit_button.pack(side=tk.LEFT, padx=5)

display_text = tk.Text(root, height=10, width=50, state=tk.DISABLED)
display_text.pack(padx=10, pady=10)
log_message("Press Start to initiate the backup")

root.mainloop()
