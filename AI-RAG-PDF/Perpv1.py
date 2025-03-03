import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import time
import os
import requests
import json
from PyPDF2 import PdfReader
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# pip install tkinter requests PyPDF2 chromadb


class AIToolGUI:
    def __init__(self, master):
        self.master = master
        master.title("AI PDF Query Tool")
        master.geometry("800x600")

        self.embedding_llm = tk.StringVar()
        self.prompt_llm = tk.StringVar()
        self.pdf_files = []
        self.chroma_client = chromadb.Client(Settings(persist_directory="./db"))
        self.collection = self.chroma_client.create_collection("pdf_collection")

        self.create_widgets()

    def create_widgets(self):
        # LLM Selection
        ttk.Label(self.master, text="Select The Embedding LLM:").pack()
        self.embedding_llm_dropdown = ttk.Combobox(self.master, textvariable=self.embedding_llm)
        self.embedding_llm_dropdown.pack()

        ttk.Label(self.master, text="Select The Prompt LLM:").pack()
        self.prompt_llm_dropdown = ttk.Combobox(self.master, textvariable=self.prompt_llm)
        self.prompt_llm_dropdown.pack()

        # Buttons
        ttk.Button(self.master, text="Load PDFs", command=self.load_pdfs).pack()
        ttk.Button(self.master, text="Process PDFs", command=self.process_pdfs).pack()
        ttk.Button(self.master, text="Run Query", command=self.run_query).pack()
        ttk.Button(self.master, text="Exit", command=self.exit_app).pack()
        ttk.Button(self.master, text="Stop", command=self.stop_execution).pack()
        ttk.Button(self.master, text="Clear Display", command=self.clear_display).pack()
        ttk.Button(self.master, text="Copy Output", command=self.copy_output).pack()
        ttk.Button(self.master, text="Show Selection", command=self.show_selection).pack()

        # Query Input
        self.query_input = tk.Text(self.master, height=3)
        self.query_input.pack()

        # Output Display
        self.output_display = tk.Text(self.master, height=20)
        self.output_display.pack()

        # Check if Ollama is running
        self.check_ollama()

    def check_ollama(self):
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                self.update_llm_list()
            else:
                messagebox.showwarning("Ollama Not Running", "Please start Ollama and restart the application.")
                self.master.quit()
        except requests.ConnectionError:
            messagebox.showwarning("Ollama Not Running", "Please start Ollama and restart the application.")
            self.master.quit()

    def update_llm_list(self):
        response = requests.get("http://localhost:11434/api/tags")
        llms = [model['name'] for model in response.json()['models']]
        self.embedding_llm_dropdown['values'] = llms
        self.prompt_llm_dropdown['values'] = llms

    def load_pdfs(self):
        self.pdf_files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        self.output_display.insert(tk.END, f"Loaded {len(self.pdf_files)} PDF files\n")

    def process_pdfs(self):
        if not self.pdf_files:
            messagebox.showwarning("No PDFs", "Please load PDFs first.")
            return

        if not self.embedding_llm.get():
            messagebox.showwarning("No Embedding LLM", "Please select an Embedding LLM.")
            return

        threading.Thread(target=self._process_pdfs, daemon=True).start()

    def _process_pdfs(self):
        self.output_display.insert(tk.END, "Processing PDFs started...\n")
        for pdf_file in self.pdf_files:
            self.output_display.insert(tk.END, f"Processing {os.path.basename(pdf_file)}...\n")
            self.master.update_idletasks()

            reader = PdfReader(pdf_file)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                self.collection.add(
                    documents=[text],
                    metadatas=[{"source": os.path.basename(pdf_file), "page": i+1}],
                    ids=[f"{os.path.basename(pdf_file)}_page_{i+1}"]
                )

                if (i + 1) % 10 == 0:
                    self.output_display.insert(tk.END, "*")
                    self.master.update_idletasks()
                    time.sleep(0.1)

            self.output_display.insert(tk.END, f"\nFinished processing {os.path.basename(pdf_file)}\n")
            self.master.update_idletasks()

        self.output_display.insert(tk.END, "PDF processing Completed.\n")

    def run_query(self):
        if not self.prompt_llm.get():
            messagebox.showwarning("No Prompt LLM", "Please select a Prompt LLM.")
            return

        query = self.query_input.get("1.0", tk.END).strip()
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a query.")
            return

        threading.Thread(target=self._run_query, args=(query,), daemon=True).start()

    def _run_query(self, query):
        self.output_display.insert(tk.END, "Processing your query...\n")
        self.master.update_idletasks()

        # Retrieve relevant documents from the vector database
        results = self.collection.query(query_texts=[query], n_results=5)

        # Prepare the context for the LLM
        context = "\n".join([doc for doc in results['documents'][0]])

        # Prepare the prompt for the LLM
        prompt = f"Context:\n{context}\n\nQuery: {query}\n\nAnswer:"

        # Send the query to Ollama
        response = requests.post("http://localhost:11434/api/generate",
                                 json={"model": self.prompt_llm.get(), "prompt": prompt})

        if response.status_code == 200:
            answer = response.json()['response']
            self.output_display.insert(tk.END, f"\nAnswer:\n{answer}\n")
        else:
            self.output_display.insert(tk.END, f"\nError processing query: {response.text}\n")

        self.master.update_idletasks()

    def exit_app(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.master.quit()

    def stop_execution(self):
        # This is a placeholder. In a real application, you'd need to implement
        # a way to stop ongoing processes.
        self.output_display.insert(tk.END, "Stopping execution...\n")

    def clear_display(self):
        self.output_display.delete("1.0", tk.END)

    def copy_output(self):
        self.master.clipboard_clear()
        self.master.clipboard_append(self.output_display.get("1.0", tk.END))

    def show_selection(self):
        info = f"Embedding LLM: {self.embedding_llm.get()}\n"
        info += f"Prompt LLM: {self.prompt_llm.get()}\n"
        info += "PDF Files:\n"
        for pdf in self.pdf_files:
            info += f"- {os.path.basename(pdf)}\n"
        self.output_display.insert(tk.END, info)

if __name__ == "__main__":
    root = tk.Tk()
    app = AIToolGUI(root)
    root.mainloop()
