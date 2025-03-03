import os
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread
from tkinter.scrolledtext import ScrolledText
import pyperclip
import time
import subprocess
import chromadb

class AIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Tool")
        self.llm_list = []

        self.init_gui()

    def init_gui(self):
        self.label_embedding_llm = tk.Label(self.root, text="Select The Embedding LLM")
        self.label_embedding_llm.grid(row=0, column=0, padx=10, pady=10)
        
        self.combo_embedding_llm = tk.StringVar()
        self.dropdown_embedding_llm = tk.OptionMenu(self.root, self.combo_embedding_llm, *self.llm_list)
        self.dropdown_embedding_llm.grid(row=0, column=1, padx=10, pady=10)
        
        self.button_load_pdfs = tk.Button(self.root, text="Load PDFs", command=self.load_pdfs)
        self.button_load_pdfs.grid(row=1, column=0, padx=10, pady=10)
        
        self.button_process_pdfs = tk.Button(self.root, text="Process PDFs", command=self.process_pdfs)
        self.button_process_pdfs.grid(row=1, column=1, padx=10, pady=10)
        
        self.label_prompt_llm = tk.Label(self.root, text="Select The Prompt LLM")
        self.label_prompt_llm.grid(row=2, column=0, padx=10, pady=10)
        
        self.combo_prompt_llm = tk.StringVar()
        self.dropdown_prompt_llm = tk.OptionMenu(self.root, self.combo_prompt_llm, *self.llm_list)
        self.dropdown_prompt_llm.grid(row=2, column=1, padx=10, pady=10)
        
        self.text_prompt = tk.Text(self.root, height=3, width=40)
        self.text_prompt.grid(row=3, column=0, columnspan=2, padx=10, pady=10)
        
        self.button_run_query = tk.Button(self.root, text="Run Query", command=self.run_query)
        self.button_run_query.grid(row=4, column=0, padx=10, pady=10)
        
        self.button_exit = tk.Button(self.root, text="Exit", command=self.exit_app)
        self.button_exit.grid(row=5, column=0, padx=10, pady=10)
        
        self.button_stop = tk.Button(self.root, text="Stop", command=self.stop_execution)
        self.button_stop.grid(row=5, column=1, padx=10, pady=10)
        
        self.button_clear_display = tk.Button(self.root, text="Clear Display", command=self.clear_display)
        self.button_clear_display.grid(row=6, column=0, padx=10, pady=10)
        
        self.button_copy_output = tk.Button(self.root, text="Copy Output", command=self.copy_output)
        self.button_copy_output.grid(row=6, column=1, padx=10, pady=10)
        
        self.button_show_selection = tk.Button(self.root, text="Show Selection", command=self.show_selection)
        self.button_show_selection.grid(row=7, column=0, columnspan=2, padx=10, pady=10)
        
        self.output_display = ScrolledText(self.root, width=80, height=20)
        self.output_display.grid(row=8, column=0, columnspan=2, padx=10, pady=10)
        
        self.load_llms()

    def load_llms(self):
        # Check if Ollama is running
        if not self.is_ollama_running():
            messagebox.showerror("Error", "Ollama is not running. Please start Ollama and try again.")
            return

        # Query Ollama for LLM list
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        self.llm_list = result.stdout.strip().split("\n")
        self.combo_embedding_llm.set(self.llm_list[0])
        self.combo_prompt_llm.set(self.llm_list[0])

    def is_ollama_running(self):
        try:
            result = subprocess.run(["ollama", "status"], capture_output=True, text=True)
            return "running" in result.stdout.lower()
        except Exception as e:
            return False

    def load_pdfs(self):
        self.pdf_files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if not self.pdf_files:
            messagebox.showwarning("Warning", "No PDF files selected.")

    def process_pdfs(self):
        if not self.pdf_files:
            messagebox.showerror("Error", "No PDF files loaded. Please load PDF files and try again.")
            return

        llm = self.combo_embedding_llm.get()
        self.output_display.insert(tk.END, "Processing PDFs started...\n")

        thread = Thread(target=self.process_pdfs_thread, args=(llm,))
        thread.start()

    def process_pdfs_thread(self, llm):
        # Initialize vector DB (ChromaDB) connection
        chromadb_client = chromadb.Client()

        for pdf_file in self.pdf_files:
            self.output_display.insert(tk.END, f"Processing {pdf_file}...\n")
            self.output_display.see(tk.END)
            self.output_display.update()

            # Process each PDF and store in vector DB
            self.process_pdf(pdf_file, llm, chromadb_client)
            
            self.output_display.insert(tk.END, "Processing complete.\n")
            self.output_display.see(tk.END)
            self.output_display.update()

        self.output_display.insert(tk.END, "PDF processing completed.\n")
        self.output_display.see(tk.END)
        self.output_display.update()

    def process_pdf(self, pdf_file, llm, chromadb_client):
        # Implement PDF processing using selected LLM and store in ChromaDB
        # (This is a placeholder function. You would need to implement the actual processing logic here.)
        time.sleep(2)  # Simulate processing time

    def run_query(self):
        llm = self.combo_prompt_llm.get()
        prompt = self.text_prompt.get("1.0", tk.END).strip()

        if not prompt:
            messagebox.showerror("Error", "No prompt provided. Please enter a prompt and try again.")
            return

        self.output_display.insert(tk.END, "Processing your query...\n")

        thread = Thread(target=self.run_query_thread, args=(llm, prompt))
        thread.start()

    def run_query_thread(self, llm, prompt):
        # Implement query processing using selected LLM and vector DB
        # (This is a placeholder function. You would need to implement the actual query processing logic here.)
        time.sleep(2)  # Simulate processing time

        self.output_display.insert(tk.END, f"Query result for '{prompt}'\n")
        self.output_display.insert(tk.END, "Query processing completed.\n")
        self.output_display.see(tk.END)
        self.output_display.update()

    def exit_app(self):
        self