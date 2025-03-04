import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import time
import os
import sys
import queue
import re
import tempfile
from pathlib import Path
import json

# For PDF processing and embedding
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama

# Optional imports that might fail on some systems
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class RAGApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF RAG Tool")
        self.root.geometry("900x1000")  # Increased height to ensure all elements are visible
        
        # Initialize state variables
        self.pdf_paths = []
        self.processing = False
        self.stop_flag = False
        self.output_queue = queue.Queue()
        self.ollama_models = []
        self.embedding_model = "llama3"  # Default embedding model
        self.query_model = "llama3"  # Default query model
        self.vector_db_path = os.path.join(tempfile.gettempdir(), "rag_vectordb")
        
        # Configuration parameters
        self.chunk_size = 1000
        self.chunk_overlap = 100
        self.top_k_results = 5
        
        # Hardware detection
        self.gpu_available = False
        self.detect_hardware()
        
        # Setup GUI components
        self.setup_gui()
        
        # Start background processes
        self.start_background_tasks()
        
    def detect_hardware(self):
        """Detect if GPU is available for acceleration"""
        if TORCH_AVAILABLE:
            self.gpu_available = torch.cuda.is_available()
            if self.gpu_available:
                self.gpu_info = f"GPU: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB"
            else:
                self.gpu_info = "GPU not detected, using CPU"
        else:
            self.gpu_info = "PyTorch not installed, using CPU"
        
    def setup_gui(self):
        """Set up the GUI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Hardware info section
        hw_frame = ttk.LabelFrame(main_frame, text="System Information", padding="5")
        hw_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(hw_frame, text=f"Hardware: {self.gpu_info}").pack(anchor=tk.W)
        
        # Status indicator
        self.status_var = tk.StringVar(value="Initializing...")
        ttk.Label(hw_frame, textvariable=self.status_var).pack(anchor=tk.W)
        
        # Model selection section
        model_frame = ttk.LabelFrame(main_frame, text="Ollama Models", padding="5")
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Embedding model selection
        embed_frame = ttk.Frame(model_frame)
        embed_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(embed_frame, text="Embedding Model:").pack(side=tk.LEFT)
        self.embed_model_var = tk.StringVar(value=self.embedding_model)
        self.embed_model_combo = ttk.Combobox(embed_frame, textvariable=self.embed_model_var)
        self.embed_model_combo.pack(side=tk.LEFT, padx=5)
        
        # Query model selection
        query_frame = ttk.Frame(model_frame)
        query_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(query_frame, text="Query Model:").pack(side=tk.LEFT)
        self.query_model_var = tk.StringVar(value=self.query_model)
        self.query_model_combo = ttk.Combobox(query_frame, textvariable=self.query_model_var)
        self.query_model_combo.pack(side=tk.LEFT, padx=5)
        
        # Processing parameters section
        param_frame = ttk.LabelFrame(main_frame, text="Processing Parameters", padding="5")
        param_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Chunk size parameter
        chunk_frame = ttk.Frame(param_frame)
        chunk_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(chunk_frame, text="Chunk Size:").pack(side=tk.LEFT)
        self.chunk_size_var = tk.IntVar(value=self.chunk_size)
        chunk_size_entry = ttk.Entry(chunk_frame, textvariable=self.chunk_size_var, width=10)
        chunk_size_entry.pack(side=tk.LEFT, padx=5)
        
        # Chunk overlap parameter
        overlap_frame = ttk.Frame(param_frame)
        overlap_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(overlap_frame, text="Chunk Overlap:").pack(side=tk.LEFT)
        self.chunk_overlap_var = tk.IntVar(value=self.chunk_overlap)
        overlap_entry = ttk.Entry(overlap_frame, textvariable=self.chunk_overlap_var, width=10)
        overlap_entry.pack(side=tk.LEFT, padx=5)
        
        # Top K results parameter
        topk_frame = ttk.Frame(param_frame)
        topk_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(topk_frame, text="Top K Results:").pack(side=tk.LEFT)
        self.topk_var = tk.IntVar(value=self.top_k_results)
        topk_entry = ttk.Entry(topk_frame, textvariable=self.topk_var, width=10)
        topk_entry.pack(side=tk.LEFT, padx=5)
        
        # PDF Selection section
        pdf_frame = ttk.LabelFrame(main_frame, text="PDF Documents", padding="5")
        pdf_frame.pack(fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(pdf_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Select PDFs", command=self.select_pdfs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Selection", command=self.clear_pdfs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Process PDFs", command=self.start_processing).pack(side=tk.LEFT, padx=5)
        
        # PDF list
        pdf_list_frame = ttk.Frame(pdf_frame)
        pdf_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.pdf_listbox = tk.Listbox(pdf_list_frame, height=5)
        self.pdf_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        pdf_scrollbar = ttk.Scrollbar(pdf_list_frame, orient=tk.VERTICAL, command=self.pdf_listbox.yview)
        pdf_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pdf_listbox.config(yscrollcommand=pdf_scrollbar.set)
        
        # Query section
        query_section = ttk.LabelFrame(main_frame, text="Query", padding="5")
        query_section.pack(fill=tk.X, padx=5, pady=5)
        
        self.query_entry = tk.Text(query_section, height=3, wrap=tk.WORD)
        self.query_entry.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(query_section, text="Submit Query", command=self.process_query).pack(anchor=tk.E, padx=5, pady=5)
        
        # Output section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate', variable=self.progress_var)
        self.progress.pack(fill=tk.X, padx=5, pady=5)
        
        # Bottom buttons section
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Stop button
        self.stop_button = ttk.Button(bottom_frame, text="Stop", command=self.stop_processing)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Clear Display button
        ttk.Button(bottom_frame, text="Clear Display", command=self.clear_display).pack(side=tk.LEFT, padx=5)
        
        # Copy Display button
        ttk.Button(bottom_frame, text="Copy Display", command=self.copy_display).pack(side=tk.LEFT, padx=5)
        
        # Exit button
        ttk.Button(bottom_frame, text="Exit", command=self.exit_application).pack(side=tk.RIGHT, padx=5)
        
    def stop_processing(self):
        """Stop ongoing processing"""
        if self.processing:
            self.stop_flag = True
            self.update_output("Stopping current operation...")
    
    def clear_display(self):
        """Clear the output display"""
        self.output_text.delete(1.0, tk.END)
    
    def copy_display(self):
        """Copy the output display to clipboard"""
        content = self.output_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.update_output("Output copied to clipboard.")
    
    def exit_application(self):
        """Gracefully exit the application"""
        if self.processing:
            if messagebox.askyesno("Exit", "Processing is in progress. Are you sure you want to exit?"):
                self.stop_flag = True
                self.root.after(500, self.root.destroy)
        else:
            self.root.destroy()
    
    def start_background_tasks(self):
        """Start background tasks"""
        # Check if Ollama is running and get available models
        threading.Thread(target=self.check_ollama_and_models, daemon=True).start()
        
        # Start output queue polling
        self.poll_output_queue()
        
    def check_ollama_and_models(self):
        """Check if Ollama server is running and get available models"""
        self.update_output("Checking if Ollama is running...")
        ollama_running = self.check_ollama_service()
        
        if not ollama_running:
            self.update_output("Ollama not running. Attempting to start Ollama server...")
            self.start_ollama()
            # Wait for Ollama to start
            time.sleep(5)
            ollama_running = self.check_ollama_service()
        
        if ollama_running:
            self.update_output("Ollama is running")
            self.status_var.set("Ollama is running")
            # Get available models
            self.update_output("Getting available models...")
            self.get_ollama_models()
        else:
            self.update_output("ERROR: Could not start Ollama service. Please start it manually.")
            self.status_var.set("ERROR: Ollama not running")
    
    def check_ollama_service(self):
        """Check if Ollama service is running"""
        try:
            # Try to list models to see if Ollama is responsive
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def start_ollama(self):
        """Start Ollama server"""
        try:
            # Start Ollama server in background
            if os.name == 'nt':  # Windows
                subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:  # Unix/Linux/Mac
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            return True
        except Exception as e:
            self.update_output(f"Error starting Ollama: {str(e)}")
            return False
    
    def get_ollama_models(self):
        """Get list of available Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                # Parse output to get model names
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header line
                    models = []
                    for line in lines[1:]:
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            models.append(model_name)
                    
                    self.ollama_models = models
                    self.update_output(f"Available models: {', '.join(models)}")
                    
                    # Update comboboxes
                    self.embed_model_combo['values'] = models
                    self.query_model_combo['values'] = models
                    
                    # Set default model if available
                    if models:
                        if "llama3" in models:
                            self.embed_model_var.set("llama3")
                            self.query_model_var.set("llama3")
                        else:
                            self.embed_model_var.set(models[0])
                            self.query_model_var.set(models[0])
            else:
                self.update_output(f"Error getting models: {result.stderr}")
        except Exception as e:
            self.update_output(f"Error getting models: {str(e)}")
    
    def select_pdfs(self):
        """Open file dialog to select PDF files"""
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if files:
            self.pdf_paths.extend(files)
            self.update_pdf_listbox()
    
    def clear_pdfs(self):
        """Clear the selected PDF files"""
        self.pdf_paths = []
        self.update_pdf_listbox()
    
    def update_pdf_listbox(self):
        """Update the PDF listbox with selected files"""
        self.pdf_listbox.delete(0, tk.END)
        for path in self.pdf_paths:
            filename = os.path.basename(path)
            self.pdf_listbox.insert(tk.END, filename)
    
    def start_processing(self):
        """Start processing the selected PDFs"""
        if not self.pdf_paths:
            messagebox.showwarning("No PDFs", "Please select at least one PDF file.")
            return
        
        if self.processing:
            messagebox.showwarning("Processing", "Already processing files. Please wait.")
            return
        
        # Get selected models and parameters
        self.embedding_model = self.embed_model_var.get()
        self.chunk_size = self.chunk_size_var.get()
        self.chunk_overlap = self.chunk_overlap_var.get()
        self.top_k_results = self.topk_var.get()
        
        # Start processing in a thread
        self.processing = True
        self.stop_flag = False
        self.progress.start(10)
        self.status_var.set("Processing PDFs...")
        
        threading.Thread(target=self.process_pdfs, daemon=True).start()
    
    def process_pdfs(self):
        """Process the selected PDF files"""
        try:
            self.update_output("\n--- Starting PDF processing ---")
            
            # Display processing parameters
            self.update_output("\nProcessing Parameters:")
            self.update_output(f"  Embedding Model: {self.embedding_model}")
            self.update_output(f"  Chunk Size: {self.chunk_size}")
            self.update_output(f"  Chunk Overlap: {self.chunk_overlap}")
            self.update_output(f"  Top K Results: {self.top_k_results}")
            self.update_output(f"  Hardware: {'GPU' if self.gpu_available else 'CPU'}")
            self.update_output(f"  Vector DB Path: {self.vector_db_path}")
            
            # Initialize vector DB
            self.update_output("\nInitializing vector database...")
            
            # Create vectorstore directory if it doesn't exist
            os.makedirs(self.vector_db_path, exist_ok=True)
            
            # Clear existing vector DB to ensure no stale data
            if os.path.exists(self.vector_db_path):
                for item in os.listdir(self.vector_db_path):
                    item_path = os.path.join(self.vector_db_path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        import shutil
                        shutil.rmtree(item_path)
            
            # Configure embedding model based on hardware
            self.update_output(f"Configuring embedding model: {self.embedding_model}")
            
            # Set up text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len
            )
            
            # Process each PDF
            all_chunks = []
            total_pages = 0
            
            for i, pdf_path in enumerate(self.pdf_paths):
                if self.stop_flag:
                    self.update_output("\nProcessing stopped by user.")
                    break
                    
                filename = os.path.basename(pdf_path)
                self.update_output(f"\nProcessing {i+1}/{len(self.pdf_paths)}: {filename}")
                
                try:
                    # Load PDF using langchain
                    loader = PyPDFLoader(pdf_path)
                    pages = loader.load()
                    total_pages += len(pages)
                    
                    # Update with progress
                    self.update_output(f"  - Loaded {len(pages)} pages")
                    
                    # Split into chunks
                    chunks = text_splitter.split_documents(pages)
                    all_chunks.extend(chunks)
                    
                    self.update_output(f"  - Split into {len(chunks)} chunks")
                    
                except Exception as e:
                    self.update_output(f"Error processing {filename}: {str(e)}")
            
            if all_chunks and not self.stop_flag:
                self.update_output(f"\nCreating vector embeddings for {len(all_chunks)} chunks from {total_pages} pages...")
                
                # Configure embedding model
                if self.gpu_available:
                    model_kwargs = {'device': 'cuda'}
                else:
                    model_kwargs = {'device': 'cpu'}
                
                # Use HuggingFace embeddings
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs=model_kwargs
                )
                
                # Create and persist vector store
                vectordb = Chroma.from_documents(
                    documents=all_chunks,
                    embedding=embeddings,
                    persist_directory=self.vector_db_path
                )
                
                vectordb.persist()
                self.update_output("Vector database created and persisted successfully!")
                self.update_output(f"Total documents: {len(all_chunks)} chunks from {total_pages} pages across {len(self.pdf_paths)} files")
            elif self.stop_flag:
                self.update_output("\nProcessing was stopped before completion.")
            else:
                self.update_output("\nNo chunks were created. Processing failed.")
            
            self.update_output("\n--- PDF processing complete ---")
            
        except Exception as e:
            self.update_output(f"Error in processing: {str(e)}")
        finally:
            self.processing = False
            self.progress.stop()
            self.status_var.set("Ready")
    
    def process_query(self):
        """Process a query against the vector DB"""
        query_text = self.query_entry.get("1.0", tk.END).strip()
        
        if not query_text:
            messagebox.showwarning("Empty Query", "Please enter a query.")
            return
        
        if self.processing:
            messagebox.showwarning("Processing", "Already processing. Please wait.")
            return
        
        if not os.path.exists(self.vector_db_path):
            messagebox.showwarning("No Data", "Please process PDFs first.")
            return
        
        # Get selected query model
        self.query_model = self.query_model_var.get()
        
        # Start query processing in a thread
        self.processing = True
        self.stop_flag = False
        self.progress.start(10)
        self.status_var.set("Processing query...")
        
        threading.Thread(target=self.execute_query, args=(query_text,), daemon=True).start()
    
    def execute_query(self, query_text):
        """Execute a query against the RAG system"""
        try:
            self.update_output("\n--- Processing Query ---")
            self.update_output(f"Query: {query_text}")
            self.update_output(f"Using model: {self.query_model}")
            self.update_output(f"Top K results: {self.top_k_results}")
            
            # Configure embedding model
            if self.gpu_available:
                model_kwargs = {'device': 'cuda'}
            else:
                model_kwargs = {'device': 'cpu'}
            
            # Use HuggingFace embeddings
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs=model_kwargs
            )
            
            # Load vectorstore
            self.update_output("Loading vector database...")
            vectordb = Chroma(
                persist_directory=self.vector_db_path,
                embedding_function=embeddings
            )
            
            # Create retriever
            retriever = vectordb.as_retriever(
                search_kwargs={"k": self.top_k_results}
            )
            
            # Get relevant documents
            self.update_output("Retrieving relevant documents...")
            docs = retriever.get_relevant_documents(query_text)
            
            if self.stop_flag:
                self.update_output("\nQuery processing stopped by user.")
                return
            
            # Configure Ollama LLM
            self.update_output(f"Configuring LLM using model: {self.query_model}")
            llm = Ollama(model=self.query_model)
            
            # Create QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            # Execute query
            self.update_output("Generating response...")
            result = qa_chain({"query": query_text})
            
            if self.stop_flag:
                self.update_output("\nQuery processing stopped by user.")
                return
            
            # Display result
            self.update_output("\n--- Response ---")
            self.update_output(result["result"])
            
            # Show sources
            self.update_output("\n--- Sources ---")
            for i, doc in enumerate(result["source_documents"]):
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "Unknown")
                self.update_output(f"Source {i+1}: {source}, Page: {page}")
            
        except Exception as e:
            self.update_output(f"Error executing query: {str(e)}")
        finally:
            self.processing = False
            self.progress.stop()
            self.status_var.set("Ready")
    
    def update_output(self, text):
        """Add text to the output queue"""
        self.output_queue.put(text)
    
    def poll_output_queue(self):
        """Poll the output queue and update the text widget"""
        try:
            while not self.output_queue.empty():
                text = self.output_queue.get(block=False)
                self.output_text.insert(tk.END, f"{text}\n")
                self.output_text.see(tk.END)
                self.output_queue.task_done()
        finally:
            # Schedule the next poll
            self.root.after(100, self.poll_output_queue)

def main():
    root = tk.Tk()
    app = RAGApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()