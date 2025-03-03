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

    # [Keep all previous methods unchanged until process_single_pdf]

    def process_single_pdf(self, path, idx):
        try:
            total_chunks = 0
            with pdfplumber.open(path) as pdf:
                documents = []
                metadatas = []
                ids = []

                for page_num, page in enumerate(pdf.pages):
                    if self.stop_flag:
                        return 0

                    try:
                        text = page.extract_text()
                        if not text:
                            continue

                        # Improved text cleaning
                        cleaned = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII characters
                        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                        
                        # Skip empty text after cleaning
                        if not cleaned:
                            continue

                        # More conservative chunking
                        words = cleaned.split()
                        chunk_size = 400
                        overlap = 50
                        
                        for i in range(0, len(words), chunk_size - overlap):
                            chunk = ' '.join(words[i:i+chunk_size])
                            if len(chunk) < 10:  # Skip tiny chunks
                                continue

                            documents.append(chunk)
                            metadatas.append({
                                "source": os.path.basename(path),
                                "page": str(page_num + 1)  # Ensure string type
                            })
                            ids.append(f"{idx}-{page_num}-{i}")

                            # Add in batches to prevent memory issues
                            if len(documents) >= 100:
                                self.collection.add(
                                    documents=documents,
                                    metadatas=metadatas,
                                    ids=ids
                                )
                                total_chunks += len(documents)
                                documents = []
                                metadatas = []
                                ids = []

                    except Exception as page_error:
                        self.update_output(f"\nPage {page_num+1} error: {str(page_error)}")

                # Add remaining documents
                if documents:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    total_chunks += len(documents)

            return total_chunks

        except Exception as e:
            self.update_output(f"\nFile error: {os.path.basename(path)} - {str(e)}\n")
            return 0

    # [Keep all remaining methods unchanged]

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFAITool(root)
    root.mainloop()