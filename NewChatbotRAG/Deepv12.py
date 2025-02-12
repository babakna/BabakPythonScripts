# pip install chromadb ollama pypdf2 python-docx openpyxl tk tqdm

import os
import subprocess
import threading
import time
import uuid
from tkinter import *
from tkinter import filedialog, messagebox, ttk

import chromadb
import ollama
from openpyxl import load_workbook
from pypdf import PdfReader
from tqdm import tqdm
from docx import Document

class RAGApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("RAG Desktop Assistant")
        self.root.geometry("800x600")
        
        self.llm_options = []
        self.current_llm = ""
        self.chroma_client = chromadb.PersistentClient(path="chroma_db")
        self.processing = False
        self.ollama_process = None
        self.uploaded_documents = []
        self.existing_ids = set()

        self.create_widgets()
        self.initialize_chroma()
        self.initialize_models()

    def initialize_models(self):
        try:
            # First check if Ollama is running
            if not self.check_ollama_running():
                self.start_ollama_server()
                time.sleep(2)
            
            # Load models directly from Ollama
            model_data = ollama.list()
            if not model_data or 'models' not in model_data:
                raise ValueError("Ollama returned unexpected response format")
            
            models = [model['name'] for model in model_data['models'] if 'name' in model]
            
            if not models:
                raise ValueError("No models found in Ollama")
            
            self.llm_options = sorted(list(set(models)), key=lambda x: x.lower())
            self.llm_combobox['values'] = self.llm_options
            
            # Set default selection
            if self.llm_options:
                self.current_llm = self.llm_options[0]
                self.llm_combobox.set(self.current_llm)
                self.update_output(f"Loaded {len(self.llm_options)} models")
            else:
                raise ValueError("No valid models found")

        except Exception as e:
            self.update_output(f"Model loading error: {str(e)}")
            self.update_output("Please ensure Ollama is running and models are installed")
            self.llm_options = []
            self.llm_combobox['values'] = []
            self.llm_combobox.set('')

    def initialize_chroma(self):
        try:
            self.chroma_client.delete_collection(name="docs")
            self.update_output("Cleared previous database entries")
        except Exception as e:
            self.update_output("No existing database found")
        
        try:
            self.collection = self.chroma_client.create_collection(name="docs")
            self.update_output("Initialized new database")
            self.uploaded_documents.clear()
            self.existing_ids.clear()
        except Exception as e:
            self.update_output(f"Database initialization failed: {str(e)}")
            raise

    def create_widgets(self):
        # Model Selection Frame
        model_frame = LabelFrame(self.root, text="LLM Selection")
        model_frame.pack(fill=X, padx=10, pady=5)
        
        self.llm_combobox = ttk.Combobox(model_frame, state="readonly", width=40)
        self.llm_combobox.pack(side=LEFT, padx=5)
        
        self.test_btn = Button(model_frame, text="Test Ollama", command=self.test_ollama_connection)
        self.test_btn.pack(side=LEFT, padx=5)
        
        self.refresh_btn = Button(model_frame, text="Refresh Models", command=self.threaded_refresh_models)
        self.refresh_btn.pack(side=LEFT, padx=5)

        # Document Management Frame
        doc_frame = LabelFrame(self.root, text="Document Management")
        doc_frame.pack(fill=X, padx=10, pady=5)
        
        self.upload_btn = Button(doc_frame, text="Upload Documents", command=self.threaded_upload_documents)
        self.upload_btn.pack(side=LEFT, padx=5)
        
        self.show_docs_btn = Button(doc_frame, text="Show Uploaded Docs", command=self.display_uploaded_documents)
        self.show_docs_btn.pack(side=LEFT, padx=5)
        
        self.reset_btn = Button(doc_frame, text="Reset Session", command=self.threaded_reset_system)
        self.reset_btn.pack(side=RIGHT, padx=5)

        # Query Interface Frame
        query_frame = LabelFrame(self.root, text="Query Interface")
        query_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        self.query_entry = Text(query_frame, height=4)
        self.query_entry.pack(fill=X, pady=5)
        
        self.run_btn = Button(query_frame, text="Run Query", command=self.threaded_run_query)
        self.run_btn.pack(side=LEFT, pady=5)
        
        self.exit_btn = Button(query_frame, text="Exit", command=self.cleanup_and_exit)
        self.exit_btn.pack(side=RIGHT, pady=5)

        # Output Display Frame
        output_frame = LabelFrame(self.root, text="Output")
        output_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        self.output_text = Text(output_frame, wrap=WORD)
        scrollbar = Scrollbar(output_frame, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        self.output_text.pack(fill=BOTH, expand=True)

        # Progress Bar
        self.progress = ttk.Progressbar(self.root, orient=HORIZONTAL, mode='indeterminate')
        self.progress.pack(fill=X, padx=10, pady=5)

    def threaded_refresh_models(self):
        threading.Thread(target=self.initialize_models).start()

    def threaded_reset_system(self):
        if not self.processing:
            threading.Thread(target=self.reset_system).start()

    def reset_system(self):
        self.set_processing(True)
        self.update_output("Initializing new session...")
        self.initialize_chroma()
        self.initialize_models()
        self.update_output("System reset completed")
        self.set_processing(False)

    def test_ollama_connection(self):
        self.set_processing(True)
        try:
            if self.check_ollama_running():
                self.update_output("Ollama is running properly!")
                self.initialize_models()
            else:
                self.update_output("Starting Ollama server...")
                if self.start_ollama_server():
                    self.update_output("Ollama started successfully!")
                    self.initialize_models()
                else:
                    self.update_output("Failed to start Ollama!")
        except Exception as e:
            self.update_output(f"Connection error: {str(e)}")
        self.set_processing(False)

    def check_ollama_running(self):
        try:
            ollama.list()
            return True
        except Exception:
            return False

    def start_ollama_server(self):
        try:
            self.ollama_process = subprocess.Popen(["ollama", "serve"], 
                                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
            time.sleep(5)
            return True
        except Exception as e:
            self.update_output(f"Error starting Ollama: {str(e)}")
            return False

    # Remaining methods (upload_documents, read_file, display_uploaded_documents, 
    # clear_output, run_query, update_output, set_processing, cleanup_and_exit) 
    # remain identical to previous version's implementation
    # ...

if __name__ == "__main__":
    root = Tk()
    app = RAGApplication(root)
    root.mainloop()