import os
import shutil
import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
import threading

# Configuration
source_paths = [
    "C:/BKUP",
    "C:/Download",
    "C:/Users/Babak/Desktop",
    "C:/Users/Babak/Documents",
    "C:/Users/Babak/Zotero"
    # Add more paths as needed
]
default_drive = "D:/"

def check_usb_drive(destination):
    if not os.path.exists(destination):
        log_message("USB drive or network path not found. Please connect the USB drive or ensure the network path is accessible and try again.")
        return False
    return True

def log_message(message):
    display_text.config(state=tk.NORMAL)
    display_text.insert(tk.END, message + '\n')
    display_text.config(state=tk.DISABLED)
    display_text.see(tk.END)

def check_source_paths():
    for source_path in source_paths:
        if not os.path.exists(source_path):
            error_message = f"Source folder not found: {source_path}"
            log_message(error_message)
            return False
    return True

def copy_with_permissions(source, destination):
    try:
        shutil.copytree(source, destination)
    except PermissionError as e:
        log_message(f"Permission denied: Skipping '{source}' due to access restrictions.")
    except Exception as e:
        log_message(f"Error copying '{source}': {str(e)}")

def create_backup(destination):
    backup_root = os.path.join(destination, "Backups")
    
    try:
        # Ensure the base destination path exists
        if not os.path.exists(destination):
            raise FileNotFoundError(f"The path '{destination}' does not exist.")
        
        # Create the backup_root directory if it doesn't exist
        if not os.path.exists(backup_root):
            result = messagebox.askyesno("Create Directory", f"The directory '{backup_root}' does not exist. Do you want to create it?")
            if result:
                os.makedirs(backup_root, exist_ok=True)
                log_message(f"Created directory: {backup_root}")
            else:
                log_message("Operation cancelled by the user.")
                return
        
        # Create the new backup directory with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        new_backup_path = os.path.join(backup_root, timestamp)
        os.makedirs(new_backup_path, exist_ok=True)
        log_message(f"Created directory: {new_backup_path}")

        # Copy the source directories to the backup location
        for source_path in source_paths:
            if os.path.exists(source_path):
                folder_name = os.path.basename(source_path)
                destination_path = os.path.join(new_backup_path, folder_name)
                log_message(f"Copying {source_path} to {destination_path}")
                copy_with_permissions(source_path, destination_path)
            else:
                error_message = f"Source folder not found: {source_path}. Skipping..."
                log_message(error_message)
        
        # Retain the latest 3 backups and delete older ones
        all_backups = sorted(Path(backup_root).iterdir(), key=os.path.getctime, reverse=True)
        if len(all_backups) > 3:
            for old_backup in all_backups[3:]:
                shutil.rmtree(old_backup)
        
        log_message("FINISHED")
        messagebox.showinfo("Backup Complete", f"Backup completed successfully!\n\nLocation: {new_backup_path}")
    except Exception as e:
        error_message = f"An error occurred during the backup process: {str(e)}"
        log_message(error_message)
        messagebox.showerror("Backup Error", error_message)

def on_start():
    try:
        destination = destination_var.get()
        if not check_usb_drive(destination):
            return
        
        if not check_source_paths():
            return

        result = messagebox.askyesno("Confirm Backup", "Do you want to start the backup?\n\nThis will create a new backup and keep the previous ones.")
        if result:
            # Start the backup process in a separate thread
            backup_thread = threading.Thread(target=create_backup, args=(destination,))
            backup_thread.start()
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        log_message(error_message)
        messagebox.showerror("Backup Error", error_message)

def on_exit():
    root.destroy()

def browse_destination():
    folder_selected = filedialog.askdirectory(initialdir=default_drive)
    if folder_selected:
        destination_var.set(folder_selected)

def display_settings():
    settings = f"Source Folders:\n" + "\n".join(source_paths) + f"\n\nDestination:\n{destination_var.get()}"
    log_message(settings)

def clear_display():
    display_text.config(state=tk.NORMAL)
    display_text.delete(1.0, tk.END)
    display_text.config(state=tk.DISABLED)

# Setup GUI
root = tk.Tk()
root.title("Backup Script")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

clear_button = tk.Button(frame, text="Clear Display", command=clear_display)
clear_button.pack(side=tk.LEFT, padx=5)

settings_button = tk.Button(frame, text="Display Settings", command=display_settings)
settings_button.pack(side=tk.LEFT, padx=5)

start_button = tk.Button(frame, text="Start Backup", command=on_start)
start_button.pack(side=tk.LEFT, padx=5)

exit_button = tk.Button(frame, text="Exit", command=on_exit)
exit_button.pack(side=tk.LEFT, padx=5)

destination_frame = tk.Frame(root)
destination_frame.pack(padx=10, pady=10)

tk.Label(destination_frame, text="Destination:").pack(side=tk.LEFT)
destination_var = tk.StringVar(value=default_drive)
destination_entry = tk.Entry(destination_frame, textvariable=destination_var, width=50)
destination_entry.pack(side=tk.LEFT, padx=5)
browse_button = tk.Button(destination_frame, text="Browse", command=browse_destination)
browse_button.pack(side=tk.LEFT, padx=5)

text_frame = tk.Frame(root)
text_frame.pack(padx=10, pady=10)

# Widen the text output area
display_text = tk.Text(text_frame, height=20, width=100, state=tk.DISABLED)
display_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=display_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
display_text.config(yscrollcommand=scrollbar.set)

log_message("Press Start to initiate the backup")

root.mainloop()