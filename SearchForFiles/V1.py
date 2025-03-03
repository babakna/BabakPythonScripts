import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import queue

class FileCounterApp:
    def __init__(self, master):
        self.master = master
        self.master.title("File Counter")
        self.master.geometry("800x600")
        
        # Variables
        self.selected_folders = []
        self.stop_flag = threading.Event()
        self.file_queue = queue.Queue()
        
        # Create GUI elements
        self.create_widgets()
        
        # Start the queue checker
        self.master.after(100, self.process_queue)
    
    def create_widgets(self):
        # Frame for buttons
        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill=tk.X)
        
        # Buttons
        ttk.Button(button_frame, text="Select Folder(s)", command=self.select_folders).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Show Folders", command=self.show_folders).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Run", command=self.start_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop", command=self.stop_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Copy Output", command=self.copy_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.master.quit).pack(side=tk.LEFT, padx=5)
        
        # Output text area
        self.output_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD)
        self.output_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
    
    def select_folders(self):
        self.selected_folders = filedialog.askdirectory(mustexist=True, title="Select Folder(s)", parent=self.master)
        if not self.selected_folders:
            return
        if isinstance(self.selected_folders, str):
            self.selected_folders = [self.selected_folders]
    
    def show_folders(self):
        if not self.selected_folders:
            messagebox.showinfo("Info", "No folders selected!")
            return
        self.output_area.insert(tk.END, "Selected Folders:\n" + "\n".join(self.selected_folders) + "\n\n")
    
    def start_search(self):
        if not self.selected_folders:
            messagebox.showerror("Error", "Please select at least one folder!")
            return
        
        self.stop_flag.clear()
        self.output_area.delete(1.0, tk.END)
        threading.Thread(target=self.run_search, daemon=True).start()
    
    def stop_search(self):
        self.stop_flag.set()
        self.file_queue.put(("stop", "Search stopped by user"))
    
    def run_search(self):
        file_types = {
            "PDF Files": [".pdf"],
            "Word Documents": [".doc", ".docx"],
            "Excel Sheets": [".xls", ".xlsx", ".xlsm"],
            "Text Files": [".txt"]
        }
        
        counts = {category: 0 for category in file_types}
        found_files = {category: [] for category in file_types}
        
        try:
            for folder in self.selected_folders:
                for root, dirs, files in os.walk(folder):
                    if self.stop_flag.is_set():
                        return
                    
                    for file in files:
                        if self.stop_flag.is_set():
                            return
                        
                        file_path = os.path.join(root, file)
                        for category, exts in file_types.items():
                            if os.path.splitext(file)[1].lower() in exts:
                                counts[category] += 1
                                found_files[category].append(file_path)
                                break
            
            # Prepare results
            result = []
            total_line = f"Found {counts['PDF Files']} PDF files, {counts['Word Documents']} Word Documents, "
            total_line += f"{counts['Excel Sheets']} Excel sheets, and {counts['Text Files']} TXT files.\n\n"
            result.append(total_line)
            
            for category in file_types:
                result.append(f"{category}\n{'=' * (len(category)+2)}\n")
                result.extend([f"{os.path.basename(f)}\n" for f in found_files[category]])
                result.append("\n")
            
            self.file_queue.put(("result", "".join(result)))
        
        except Exception as e:
            self.file_queue.put(("error", f"Error: {str(e)}"))
    
    def process_queue(self):
        try:
            while True:
                msg_type, content = self.file_queue.get_nowait()
                if msg_type == "result":
                    self.output_area.insert(tk.END, content)
                elif msg_type == "error":
                    self.output_area.insert(tk.END, content + "\n")
                elif msg_type == "stop":
                    self.output_area.insert(tk.END, content + "\n")
        except queue.Empty:
            pass
        self.master.after(100, self.process_queue)
    
    def copy_output(self):
        self.master.clipboard_clear()
        self.master.clipboard_append(self.output_area.get(1.0, tk.END))
    
    def clear_output(self):
        self.output_area.delete(1.0, tk.END)
        self.selected_folders = []
        self.stop_flag.set()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileCounterApp(root)
    root.mainloop()