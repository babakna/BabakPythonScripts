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
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import ollama
from dotenv import load_dotenv

load_dotenv()

class PDFAITool:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF AI Tool")
        self.root.geometry("800x900")
        
        # Hardware configuration
        self.gpu_available = False
        self.gpu_info = ""
        self.chroma_settings = Settings()
        self.detect_hardware()
        
        # Application state
        self.ollama_running = False
        self.ollama_process = None
        self.processing = False
        self.stop_flag = False
        self.pdf_paths = []
        self.output_queue = queue.Queue()
        self.chroma_client = chromadb.Client(self.chroma_settings)
        self.collection = None
        
        # Initialize components
        self.setup_gui()
        self.check_ollama()
        self.initialize_chromadb()
        self.poll_output_queue()
        self.report_hardware()

    def detect_hardware(self):
        try:
            import torch
            if torch.cuda.is_available():
                self.gpu_available = True
                self.gpu_info = (f"GPU Detected: {torch.cuda.get_device_name(0)}\n"
                                f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")
                self.chroma_settings.allow_reset = True
                self.chroma_settings.is_persistent = True
        except ImportError:
            self.gpu_available = False
            self.gpu_info = "PyTorch not installed, using CPU"

    def report_hardware(self):
        if self.gpu_available:
            self.update_output(f"Hardware: Using GPU acceleration\n{self.gpu_info}\n")
        else:
            self.update_output("Hardware: Using CPU\n")

    def initialize_chromadb(self):
        try:
            existing_collections = [col.name for col in self.chroma_client.list_collections()]
            if "pdf_collection" in existing_collections:
                self.chroma_client.delete_collection("pdf_collection")
            self.collection = self.chroma_client.create_collection("pdf_collection")
        except Exception:
            pass

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Hardware Info Button
        hw_frame = ttk.Frame(main_frame)
        hw_frame.pack(fill=tk.X, pady=5)
        ttk.Button(hw_frame, text="CPU/GPU Info", command=self.show_hardware_info).pack(side=tk.LEFT)

        # Model Selection
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

        # PDF Controls
        pdf_frame = ttk.LabelFrame(main_frame, text="PDF Processing", padding=10)
        pdf_frame.pack(fill=tk.X, pady=5)

        ttk.Button(pdf_frame, text="Load PDFs", command=self.load_pdfs).grid(row=0, column=0, padx=5)
        ttk.Button(pdf_frame, text="Process PDFs", command=self.process_pdfs).grid(row=0, column=1, padx=5)
        ttk.Button(pdf_frame, text="Show Selection", command=self.show_selection).grid(row=0, column=2, padx=5)

        # Query Section
        query_frame = ttk.LabelFrame(main_frame, text="Query", padding=10)
        query_frame.pack(fill=tk.X, pady=5)

        self.query_entry = tk.Text(query_frame, height=3, width=70)
        self.query_entry.pack(pady=5)
        self.query_entry.config(state=tk.DISABLED)
        self.run_query_btn = ttk.Button(query_frame, text="Run Query", command=self.run_query)
        self.run_query_btn.pack(pady=5)
        self.run_query_btn.config(state=tk.DISABLED)

        # Output
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Control Buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Button(control_frame, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Copy", command=self.copy_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_process).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Exit", command=self.exit_app).pack(side=tk.RIGHT, padx=5)

    def show_hardware_info(self):
        if self.gpu_available:
            info = f"Active Hardware: GPU\n{self.gpu_info}"
        else:
            info = "Active Hardware: CPU\n(No compatible GPU detected)"
        messagebox.showinfo("Hardware Information", info)

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
        except Exception as e:
            self.show_error(f"Failed to start Ollama: {str(e)}")
            self.root.destroy()

    def wait_for_ollama_ready(self, max_attempts=5, delay=3):
        for _ in range(max_attempts):
            try:
                ollama.list()
                self.ollama_running = True
                self.populate_models()
                return
            except Exception:
                time.sleep(delay)
        self.show_error("Ollama failed to start")
        self.root.destroy()

    def populate_models(self):
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            models = []
            for line in result.stdout.split('\n')[1:]:
                if line.strip():
                    models.append(line.split()[0])
            if models:
                self.embedding_dropdown['values'] = models
                self.prompt_dropdown['values'] = models
                self.embedding_model.set(models[0])
                self.prompt_model.set(models[0])
                self.update_output("Models loaded successfully\n")
        except Exception as e:
            self.show_error(f"Model error: {str(e)}")

    def toggle_ui_state(self, processing):
        state = tk.DISABLED if processing else tk.NORMAL
        self.query_entry.config(state=state)
        self.run_query_btn.config(state=state)
        self.embedding_dropdown.config(state=state)
        self.prompt_dropdown.config(state=state)

    def load_pdfs(self):
        self.pdf_paths = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        self.update_output(f"Loaded {len(self.pdf_paths)} PDF(s)\n")

    def process_pdfs(self):
        if not self.pdf_paths:
            self.show_error("No PDFs selected!")
            return
        
        self.processing = True
        self.stop_flag = False
        self.toggle_ui_state(True)
        self.update_output("\n=== Processing Started ===\n")
        self.update_output(f"Using: {'GPU' if self.gpu_available else 'CPU'}\n")
        threading.Thread(target=self.process_pdfs_thread, daemon=True).start()
        self.start_progress_indicator()

    def start_progress_indicator(self):
        if self.processing:
            self.output_queue.put("* ")
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
                
                chunks = self.process_single_pdf(path, idx)
                total_chunks += chunks
                self.update_output(f"Processed {os.path.basename(path)} ({chunks} chunks)\n")

            self.update_output(f"\n=== Processing Complete ===\nTotal chunks: {total_chunks}\n")

        except Exception as e:
            self.update_output(f"\nProcessing error: {str(e)}\n")
        finally:
            self.processing = False
            self.toggle_ui_state(False)

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
                        words = cleaned.split()
                        chunk_size = 500
                        overlap = 100
                        
                        for i in range(0, len(words), chunk_size - overlap):
                            chunk = ' '.join(words[i:i+chunk_size])
                            documents.append(chunk)
                            metadatas.append({
                                "source": os.path.basename(path),
                                "page": page_num + 1
                            })
                            ids.append(f"{idx}-{page_num}-{i}")

                if documents:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    return len(documents)
                return 0

        except Exception as e:
            self.update_output(f"\nFile error: {os.path.basename(path)} - {str(e)}\n")
            return 0

    def run_query(self):
        query = self.query_entry.get("1.0", tk.END).strip()
        if not query:
            return
        
        self.update_output(f"\nStarting query using {'GPU' if self.gpu_available else 'CPU'}...\n")
        threading.Thread(target=self.run_query_thread, args=(query,), daemon=True).start()

    def run_query_thread(self, query):
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=3,
                include=["documents", "metadatas"]
            )
            
            context = "\n".join([
                f"[Source: {meta['source']} Page {meta['page']}]\n{text}\n"
                for text, meta in zip(results['documents'][0], results['metadatas'][0])
            ])
            
            response = ollama.generate(
                model=self.prompt_model.get(),
                prompt=f"Context:\n{context}\nQuestion: {query}\nAnswer:"
            )
            self.update_output(f"\nRESPONSE:\n{response['response']}\n")
            
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
        info = f"Embedding Model: {self.embedding_model.get()}\n"
        info += f"Prompt Model: {self.prompt_model.get()}\n"
        info += "Loaded PDFs:\n" + "\n".join(os.path.basename(p) for p in self.pdf_paths)
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