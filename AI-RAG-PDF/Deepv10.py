import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import time
import os
import sys
import queue
import re
import pdfplumber
import chromadb
from chromadb.utils import embedding_functions
import ollama
from dotenv import load_dotenv

load_dotenv()

class PDFAITool:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF AI Tool")
        self.root.geometry("800x900")
        
        self.ollama_running = False
        self.ollama_process = None
        self.processing = False
        self.stop_flag = False
        self.pdf_paths = []
        self.output_queue = queue.Queue()
        self.chroma_client = chromadb.Client()
        self.collection = None
        
        self.setup_gui()
        self.check_ollama()
        self.poll_output_queue()
        self.initialize_chromadb()

    def initialize_chromadb(self):
        try:
            # Delete existing collection if it exists
            if self.chroma_client.get_collection("pdf_collection"):
                self.chroma_client.delete_collection("pdf_collection")
            self.collection = self.chroma_client.create_collection("pdf_collection")
        except Exception as e:
            self.update_output(f"Error initializing ChromaDB: {str(e)}\n")

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        model_frame = ttk.LabelFrame(main_frame, text="Model Selection", padding=10)
        model_frame.pack(fill=tk.X, pady=5)

        ttk.Label(model_frame, text="Embedding LLM:").grid(row=0, column=0, padx=5)
        self.embedding_model = tk.StringVar()
        self.embedding_dropdown = ttk.Combobox(model_frame, textvariable=self.embedding_model)
        self.embedding_dropdown.grid(row=0, column=1, padx=5)

        ttk.Label(model_frame, text="Prompt LLM:").grid(row=0, column=2, padx=5)
        self.prompt_model = tk.StringVar()
        self.prompt_dropdown = ttk.Combobox(model_frame, textvariable=self.prompt_model)
        self.prompt_dropdown.grid(row=0, column=3, padx=5)

        pdf_frame = ttk.LabelFrame(main_frame, text="PDF Processing", padding=10)
        pdf_frame.pack(fill=tk.X, pady=5)

        ttk.Button(pdf_frame, text="Load PDFs", command=self.load_pdfs).grid(row=0, column=0, padx=5)
        ttk.Button(pdf_frame, text="Process PDFs", command=self.process_pdfs).grid(row=0, column=1, padx=5)
        ttk.Button(pdf_frame, text="Show Selection", command=self.show_selection).grid(row=0, column=2, padx=5)

        query_frame = ttk.LabelFrame(main_frame, text="Query", padding=10)
        query_frame.pack(fill=tk.X, pady=5)

        self.query_entry = tk.Text(query_frame, height=3, width=70)
        self.query_entry.pack(pady=5)
        ttk.Button(query_frame, text="Run Query", command=self.run_query).pack(pady=5)

        output_frame = ttk.LabelFrame(main_frame, text="Output", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Button(control_frame, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Copy", command=self.copy_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_process).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Exit", command=self.exit_app).pack(side=tk.RIGHT, padx=5)

    def check_ollama(self):
        try:
            ollama.list()
            self.ollama_running = True
            self.populate_models()
        except Exception:
            self.attempt_start_ollama()

    def attempt_start_ollama(self):
        self.update_output("Starting Ollama server...\n")
        try:
            self.ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self.wait_for_ollama_ready()
        except FileNotFoundError:
            self.show_error("Ollama not installed! Download from https://ollama.ai/")
            self.root.destroy()
        except Exception as e:
            self.show_error(f"Failed to start Ollama: {str(e)}")
            self.root.destroy()

    def wait_for_ollama_ready(self, max_attempts=5, delay=3):
        for _ in range(max_attempts):
            try:
                ollama.list()
                self.ollama_running = True
                self.populate_models()
                self.update_output("Ollama server ready\n")
                return
            except Exception:
                time.sleep(delay)
        self.show_error("Ollama failed to start")
        self.root.destroy()

    def populate_models(self):
        try:
            models = []
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines[1:]:
                    if line.strip():
                        model_name = line.split()[0]
                        models.append(model_name)
            
            if models:
                self.embedding_dropdown['values'] = models
                self.prompt_dropdown['values'] = models
                self.embedding_model.set(models[0])
                self.prompt_model.set(models[0])
            else:
                self.show_error("No models found. Install one first!")
        except Exception as e:
            self.show_error(f"Error loading models: {str(e)}")

    def load_pdfs(self):
        self.pdf_paths = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        self.update_output(f"Loaded {len(self.pdf_paths)} PDF(s)\n")

    def process_pdfs(self):
        if not self.pdf_paths:
            self.show_error("No PDFs selected!")
            return
        if not self.ollama_running:
            self.show_error("Ollama not ready!")
            return

        self.processing = True
        self.stop_flag = False
        self.update_output("\nStarting PDF processing...\n")
        threading.Thread(target=self.process_pdfs_thread, daemon=True).start()
        self.start_progress_indicator()

    def start_progress_indicator(self):
        if self.processing:
            self.output_queue.put("*")
            self.root.after(30000, self.start_progress_indicator)

    def process_pdfs_thread(self):
        try:
            embedding_func = embedding_functions.OllamaEmbeddingFunction(
                model_name=self.embedding_model.get(),
                url="http://localhost:11434"
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name="pdf_collection",
                embedding_function=embedding_func
            )

            total_chunks = 0
            for idx, path in enumerate(self.pdf_paths):
                if self.stop_flag:
                    break
                
                self.update_output(f"\nProcessing {os.path.basename(path)}...")
                chunks_added = self.process_single_pdf(path, idx)
                total_chunks += chunks_added
                self.update_output(f" - Added {chunks_added} chunks")

            self.update_output(f"\n\nProcessing complete. Total chunks processed: {total_chunks}\n")

        except Exception as e:
            self.update_output(f"\nProcessing failed: {str(e)}\n")
        finally:
            self.processing = False

    def process_single_pdf(self, path, idx):
        try:
            with pdfplumber.open(path) as pdf:
                documents = []
                metadatas = []
                ids = []

                for page_num, page in enumerate(pdf.pages):
                    if self.stop_flag:
                        return 0

                    text = page.extract_text()
                    if text:
                        cleaned = re.sub(r'\s+', ' ', text).strip()
                        cleaned = ''.join(c for c in cleaned if c.isprintable())
                        words = cleaned.split()
                        max_words = 300
                        overlap = 50
                        start = 0
                        while start < len(words):
                            end = min(start + max_words, len(words))
                            chunk = ' '.join(words[start:end])
                            documents.append(chunk)
                            metadatas.append({
                                "source": os.path.basename(path),
                                "page": page_num + 1
                            })
                            ids.append(f"doc_{idx}_p{page_num}_c{start}")
                            start = end - overlap

                if documents:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    return len(documents)
                return 0

        except Exception as e:
            self.update_output(f"\nError processing {os.path.basename(path)}: {str(e)}")
            return 0

    def run_query(self):
        query = self.query_entry.get("1.0", tk.END).strip()
        if not query:
            return
        threading.Thread(target=self.run_query_thread, args=(query,), daemon=True).start()

    def run_query_thread(self, query):
        try:
            self.update_output("\nProcessing query...\n")
            if not self.collection:
                raise ValueError("No documents processed yet")

            results = self.collection.query(
                query_texts=[query],
                n_results=3,
                include=["documents", "metadatas"]
            )

            if not results['documents']:
                raise ValueError("No results found")

            context = "\n\n".join([
                f"Source: {meta['source']} (Page {meta['page']})\n{text}"
                for text, meta in zip(results['documents'][0], results['metadatas'][0])
            ])

            response = ollama.generate(
                model=self.prompt_model.get(),
                prompt=f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
            )
            self.update_output(f"\nResponse:\n{response['response']}\n")

        except Exception as e:
            self.update_output(f"\nQuery failed: {str(e)}\n")

    def update_output(self, message):
        self.output_queue.put(message)

    def poll_output_queue(self):
        while not self.output_queue.empty():
            msg = self.output_queue.get_nowait()
            self.output_text.insert(tk.END, msg)
            self.output_text.see(tk.END)
        self.root.after(100, self.poll_output_queue)

    def show_selection(self):
        info = f"Models:\nEmbedding: {self.embedding_model.get()}\nPrompt: {self.prompt_model.get()}\n"
        info += f"Loaded PDFs:\n" + "\n".join(os.path.basename(p) for p in self.pdf_paths)
        self.update_output(f"\nCurrent Selection:\n{info}\n")

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)

    def copy_output(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output_text.get(1.0, tk.END))

    def stop_process(self):
        self.stop_flag = True
        self.update_output("\nProcess stopped by user\n")

    def exit_app(self):
        if messagebox.askyesno("Exit", "Are you sure?"):
            if self.ollama_process:
                self.ollama_process.terminate()
            self.root.destroy()

    def show_error(self, message):
        messagebox.showerror("Error", message)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFAITool(root)
    root.mainloop()