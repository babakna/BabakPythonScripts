import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import subprocess
import time
import os
import queue
import sys
import json
import re
from PIL import Image
import pytesseract
import PyPDF2
from io import BytesIO
import chromadb
import numpy as np
import pyperclip
import tempfile
from pathlib import Path
import hashlib


class OllamaAITool:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama PDF AI Tool")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # State variables
        self.stop_execution = False
        self.embedding_llm = tk.StringVar()
        self.prompt_llm = tk.StringVar()
        self.selected_pdfs = []
        self.ollama_models = []
        self.output_queue = queue.Queue()
        self.processing_thread = None
        self.vector_db = None
        self.db_client = None
        self.collection = None
        
        # Temp directory for image extraction from PDFs
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Initialize GUI
        self.init_gui()
        
        # Schedule the Ollama check
        self.root.after(100, self.check_ollama)
        
        # Set up periodic queue check for output
        self.check_output_queue()

    def init_gui(self):
        # Create frames
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        mid_frame = ttk.Frame(self.root, padding=10)
        mid_frame.pack(fill=tk.X)
        
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top frame components - LLM selection
        ttk.Label(top_frame, text="Select The Embedding LLM:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.embedding_llm_dropdown = ttk.Combobox(top_frame, textvariable=self.embedding_llm, state="readonly", width=30)
        self.embedding_llm_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(top_frame, text="Select The Prompt LLM:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.prompt_llm_dropdown = ttk.Combobox(top_frame, textvariable=self.prompt_llm, state="readonly", width=30)
        self.prompt_llm_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # PDF buttons
        pdf_frame = ttk.Frame(top_frame)
        pdf_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=5, sticky=tk.E)
        
        self.load_pdf_btn = ttk.Button(pdf_frame, text="Load PDFs", command=self.load_pdfs)
        self.load_pdf_btn.pack(pady=2)
        
        self.process_pdfs_btn = ttk.Button(pdf_frame, text="Process PDFs", command=self.process_pdfs)
        self.process_pdfs_btn.pack(pady=2)
        
        # Mid frame - Query input
        ttk.Label(mid_frame, text="Enter your query:").pack(anchor=tk.W, padx=5)
        self.query_text = scrolledtext.ScrolledText(mid_frame, height=3, width=80, wrap=tk.WORD)
        self.query_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Query buttons
        query_buttons_frame = ttk.Frame(mid_frame)
        query_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.run_query_btn = ttk.Button(query_buttons_frame, text="Run Query", command=self.run_query)
        self.run_query_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(query_buttons_frame, text="Stop", command=self.stop_execution_cmd)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_display_btn = ttk.Button(query_buttons_frame, text="Clear Display", command=self.clear_display)
        self.clear_display_btn.pack(side=tk.LEFT, padx=5)
        
        self.copy_output_btn = ttk.Button(query_buttons_frame, text="Copy Output", command=self.copy_output)
        self.copy_output_btn.pack(side=tk.LEFT, padx=5)
        
        self.show_selection_btn = ttk.Button(query_buttons_frame, text="Show Selection", command=self.show_selection)
        self.show_selection_btn.pack(side=tk.LEFT, padx=5)
        
        self.exit_btn = ttk.Button(query_buttons_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side=tk.RIGHT, padx=5)
        
        # Bottom frame - Output display
        ttk.Label(bottom_frame, text="Output:").pack(anchor=tk.W, padx=5)
        self.output_display = scrolledtext.ScrolledText(bottom_frame, height=15, width=80, wrap=tk.WORD)
        self.output_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_display.config(state=tk.DISABLED)
        
        # Apply some basic styling
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TLabel", font=("Segoe UI", 10))
        
        # Initially disable some buttons
        self.process_pdfs_btn.config(state=tk.DISABLED)
        self.run_query_btn.config(state=tk.DISABLED)

    def check_ollama(self):
        self.log_output("Checking if Ollama is running...")
        
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_output("Ollama is running.")
                self.fetch_ollama_models()
            else:
                self.log_output("Ollama is not running. Please start Ollama and restart the application.")
                self.prompt_start_ollama()
        except FileNotFoundError:
            self.log_output("Ollama is not installed or not in PATH. Please install Ollama first.")
        except Exception as e:
            self.log_output(f"Error checking Ollama: {str(e)}")

    def prompt_start_ollama(self):
        # Create a dialog to prompt the user to start Ollama
        prompt_window = tk.Toplevel(self.root)
        prompt_window.title("Start Ollama")
        prompt_window.geometry("400x150")
        prompt_window.transient(self.root)
        prompt_window.grab_set()
        
        ttk.Label(prompt_window, text="Ollama is not running. Please start Ollama and click 'Retry'.", 
                 wraplength=380, justify=tk.CENTER).pack(pady=20)
        
        buttons_frame = ttk.Frame(prompt_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Retry", command=lambda: [prompt_window.destroy(), self.check_ollama()]).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Exit", command=self.exit_app).pack(side=tk.LEFT, padx=10)

    def fetch_ollama_models(self):
        self.log_output("Fetching available Ollama models...")
        
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse the output to get model names
                output_lines = result.stdout.strip().split("\n")
                # Skip the header line
                model_lines = output_lines[1:] if len(output_lines) > 1 else []
                
                models = []
                for line in model_lines:
                    # Extract the model name (first column)
                    match = re.match(r'(\S+)', line)
                    if match:
                        models.append(match.group(1))
                
                if models:
                    self.ollama_models = models
                    self.log_output(f"Found {len(models)} models: {', '.join(models)}")
                    self.update_model_dropdowns()
                else:
                    self.log_output("No models found. Please pull at least one model using 'ollama pull <model>'.")
            else:
                self.log_output("Failed to fetch models. Error: " + result.stderr)
        except Exception as e:
            self.log_output(f"Error fetching models: {str(e)}")

    def update_model_dropdowns(self):
        # Update both dropdown menus with available models
        self.embedding_llm_dropdown['values'] = self.ollama_models
        self.prompt_llm_dropdown['values'] = self.ollama_models
        
        # Select the first model by default if available
        if self.ollama_models:
            self.embedding_llm.set(self.ollama_models[0])
            self.prompt_llm.set(self.ollama_models[0])
            
            # Enable the Load PDFs button
            self.load_pdf_btn.config(state=tk.NORMAL)
        else:
            self.embedding_llm.set("")
            self.prompt_llm.set("")
            self.load_pdf_btn.config(state=tk.DISABLED)

    def load_pdfs(self):
        filetypes = [("PDF files", "*.pdf")]
        filenames = filedialog.askopenfilenames(title="Select PDF Files", filetypes=filetypes)
        
        if filenames:
            # Limit to 10 PDFs as specified
            self.selected_pdfs = list(filenames)[:10]
            if len(filenames) > 10:
                self.log_output("Warning: Maximum 10 PDFs allowed. Only the first 10 will be processed.")
            
            self.log_output(f"Selected {len(self.selected_pdfs)} PDF files:")
            for pdf in self.selected_pdfs:
                self.log_output(f" - {os.path.basename(pdf)}")
            
            # Enable process button
            self.process_pdfs_btn.config(state=tk.NORMAL)
        else:
            self.log_output("No PDF files selected.")

    def process_pdfs(self):
        if not self.selected_pdfs:
            self.log_output("No PDFs selected. Please load PDFs first.")
            return
        
        if not self.embedding_llm.get():
            self.log_output("No embedding LLM selected. Please select an LLM for embedding.")
            return
        
        # Disable buttons during processing
        self.disable_buttons_during_processing()
        
        # Reset stop flag
        self.stop_execution = False
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.process_pdfs_thread)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def process_pdfs_thread(self):
        try:
            self.log_output("PDF processing started...")
            
            # Initialize ChromaDB
            self.init_vector_db()
            
            # Process each PDF file
            for i, pdf_path in enumerate(self.selected_pdfs):
                if self.stop_execution:
                    self.log_output("PDF processing stopped.")
                    break
                
                pdf_name = os.path.basename(pdf_path)
                self.log_output(f"Processing PDF {i+1}/{len(self.selected_pdfs)}: {pdf_name}")
                
                # Process the PDF and add to vector DB
                self.process_single_pdf(pdf_path)
                
                # Check if processing is stopped
                if self.stop_execution:
                    self.log_output("PDF processing stopped.")
                    break
            
            if not self.stop_execution:
                self.log_output("PDF processing completed.")
                # Enable the run query button once processing is complete
                self.root.after(0, lambda: self.run_query_btn.config(state=tk.NORMAL))
            
        except Exception as e:
            self.log_output(f"Error processing PDFs: {str(e)}")
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_buttons_after_processing)

    def init_vector_db(self):
        try:
            self.log_output("Initializing vector database...")
            
            # Create a persistent ChromaDB client
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
            os.makedirs(db_path, exist_ok=True)
            
            self.db_client = chromadb.PersistentClient(path=db_path)
            
            # Create a unique collection name based on the selected PDFs
            collection_id = self.generate_collection_id()
            
            # Try to get existing collection or create a new one
            try:
                self.collection = self.db_client.get_collection(name=collection_id)
                self.log_output(f"Using existing collection: {collection_id}")
            except:
                # Create a new collection with the Ollama embedding function
                embedding_func = self.create_ollama_embedding_function()
                self.collection = self.db_client.create_collection(
                    name=collection_id,
                    embedding_function=embedding_func
                )
                self.log_output(f"Created new collection: {collection_id}")
            
        except Exception as e:
            self.log_output(f"Error initializing vector database: {str(e)}")
            raise

    def create_ollama_embedding_function(self):
        # Create a custom embedding function that uses Ollama
        class OllamaEmbeddingFunction:
            def __init__(self, model_name):
                self.model_name = model_name
            
            def __call__(self, texts):
                embeddings = []
                for text in texts:
                    if not text.strip():
                        # Handle empty text by returning zero vector
                        embeddings.append(np.zeros(1536).tolist())  # Default embedding size
                        continue
                    
                    try:
                        cmd = ["ollama", "embeddings", "-m", self.model_name]
                        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                                 stderr=subprocess.PIPE, text=True)
                        stdout, stderr = process.communicate(input=text)
                        
                        if process.returncode != 0:
                            raise Exception(f"Ollama embedding error: {stderr}")
                        
                        # Parse the JSON response
                        response = json.loads(stdout)
                        embedding = response.get("embedding", [])
                        embeddings.append(embedding)
                    except Exception as e:
                        print(f"Error generating embedding: {str(e)}")
                        # Return a zero vector as fallback
                        embeddings.append(np.zeros(1536).tolist())
                
                return embeddings
        
        return OllamaEmbeddingFunction(self.embedding_llm.get())

    def generate_collection_id(self):
        # Create a unique identifier based on the selected PDFs and embedding model
        pdf_names = [os.path.basename(pdf) for pdf in self.selected_pdfs]
        pdf_names.sort()  # Sort to ensure consistent order
        
        # Combine PDF names and embedding model
        source_string = f"{','.join(pdf_names)}_{self.embedding_llm.get()}"
        
        # Create a hash of the source string
        hash_obj = hashlib.md5(source_string.encode())
        collection_id = f"ollama_pdfs_{hash_obj.hexdigest()[:10]}"
        
        return collection_id

    def process_single_pdf(self, pdf_path):
        try:
            pdf_name = os.path.basename(pdf_path)
            
            # Open the PDF with PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
                
                # Process each page with progress indicators
                for page_num in range(total_pages):
                    if self.stop_execution:
                        break
                    
                    # Show progress every 30 seconds or for every 5 pages
                    if page_num % 5 == 0:
                        self.log_output(f"Processing page {page_num+1}/{total_pages} of {pdf_name}")
                    else:
                        self.log_output("*", end="")
                    
                    # Get the page
                    page = reader.pages[page_num]
                    
                    # Extract text from the page
                    text = page.extract_text()
                    
                    # Skip if page is empty
                    if not text or not text.strip():
                        continue
                    
                    # Split text into chunks (~ 1000 characters each)
                    chunks = self.chunk_text(text, 1000)
                    
                    # Add chunks to vector database
                    for i, chunk in enumerate(chunks):
                        if self.stop_execution:
                            break
                        
                        # Create unique ID for this chunk
                        chunk_id = f"{pdf_name}_p{page_num}_c{i}"
                        
                        # Add to collection
                        self.collection.add(
                            documents=[chunk],
                            metadatas=[{"source": pdf_name, "page": page_num + 1}],
                            ids=[chunk_id]
                        )
                
        except Exception as e:
            self.log_output(f"Error processing PDF {pdf_name}: {str(e)}")

    def chunk_text(self, text, chunk_size=1000, overlap=100):
        # Split text into chunks with some overlap
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # Adjust end to not break in the middle of a sentence
            if end < text_length:
                # Try to find the end of a sentence
                for i in range(min(100, end - start)):
                    if text[end - i - 1] in ['.', '!', '?', '\n'] and (end - i < text_length and text[end - i] in [' ', '\n']):
                        end = end - i
                        break
            
            chunks.append(text[start:end])
            start = end - overlap
            
            # Check for stop signal
            if self.stop_execution:
                break
        
        return chunks

    def run_query(self):
        query = self.query_text.get("1.0", tk.END).strip()
        
        if not query:
            self.log_output("Please enter a query.")
            return
        
        if not self.prompt_llm.get():
            self.log_output("No prompt LLM selected. Please select an LLM for querying.")
            return
        
        if not hasattr(self, 'collection') or self.collection is None:
            self.log_output("No data has been processed yet. Please process PDFs first.")
            return
        
        # Disable buttons during processing
        self.disable_buttons_during_processing()
        
        # Reset stop flag
        self.stop_execution = False
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(target=self.run_query_thread, args=(query,))
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def run_query_thread(self, query):
        try:
            self.log_output("Processing your query...")
            
            # Get relevant chunks from vector DB
            results = self.collection.query(
                query_texts=[query],
                n_results=10  # Adjust based on needed context
            )
            
            # Get the documents and their metadata
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            
            if not documents:
                self.log_output("No relevant information found for your query.")
                return
            
            # Prepare context from the retrieved documents
            context = ""
            for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                source = meta.get('source', 'Unknown')
                page = meta.get('page', 'Unknown')
                context += f"\n--- Excerpt {i+1} from {source} (Page {page}) ---\n{doc}\n"
            
            # Prepare the prompt
            system_prompt = """You are an AI assistant that helps answer questions based on the provided context.
            Use only the information from the context to answer the query. If the answer is not in the context,
            say that you don't have enough information to answer accurately. Cite the sources (document name and page)
            where you found the information."""
            
            prompt = f"""System: {system_prompt}
            
            Context:
            {context}
            
            User Query: {query}
            
            Answer:"""
            
            # Call Ollama to generate the answer
            self.log_output("Generating answer based on the relevant information...")
            
            cmd = ["ollama", "run", self.prompt_llm.get()]
            process = subprocess.Popen(
                cmd, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Send the prompt
            process.stdin.write(prompt)
            process.stdin.close()
            
            # Read and display the response in real-time
            answer = ""
            for line in process.stdout:
                if self.stop_execution:
                    process.terminate()
                    self.log_output("\nQuery processing stopped.")
                    break
                
                answer += line
                self.log_output(line, end="")
            
            # Check for errors
            stderr = process.stderr.read()
            if stderr:
                self.log_output(f"\nError: {stderr}")
            
            process.wait()
            
            if not self.stop_execution:
                self.log_output("\nQuery processing completed.")
            
        except Exception as e:
            self.log_output(f"\nError processing query: {str(e)}")
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_buttons_after_processing)

    def stop_execution_cmd(self):
        self.stop_execution = True
        self.log_output("Stopping current operation...")
        
        # If there's an active thread, wait for it to recognize the stop flag
        if self.processing_thread and self.processing_thread.is_alive():
            # Enable buttons after stopping
            self.enable_buttons_after_processing()

    def disable_buttons_during_processing(self):
        self.load_pdf_btn.config(state=tk.DISABLED)
        self.process_pdfs_btn.config(state=tk.DISABLED)
        self.run_query_btn.config(state=tk.DISABLED)
        self.embedding_llm_dropdown.config(state=tk.DISABLED)
        self.prompt_llm_dropdown.config(state=tk.DISABLED)

    def enable_buttons_after_processing(self):
        self.load_pdf_btn.config(state=tk.NORMAL)
        self.process_pdfs_btn.config(state=tk.NORMAL if self.selected_pdfs else tk.DISABLED)
        self.run_query_btn.config(state=tk.NORMAL if hasattr(self, 'collection') and self.collection is not None else tk.DISABLED)
        self.embedding_llm_dropdown.config(state="readonly")
        self.prompt_llm_dropdown.config(state="readonly")

    def clear_display(self):
        self.output_display.config(state=tk.NORMAL)
        self.output_display.delete(1.0, tk.END)
        self.output_display.config(state=tk.DISABLED)

    def copy_output(self):
        output_text = self.output_display.get(1.0, tk.END).strip()
        if output_text:
            pyperclip.copy(output_text)
            self.log_output("Output copied to clipboard.")
        else:
            self.log_output("No output to copy.")

    def show_selection(self):
        self.log_output("\n--- Current Selection ---")
        self.log_output(f"Embedding LLM: {self.embedding_llm.get()}")
        self.log_output(f"Prompt LLM: {self.prompt_llm.get()}")
        self.log_output("Selected PDFs:")
        for i, pdf in enumerate(self.selected_pdfs):
            self.log_output(f"{i+1}. {os.path.basename(pdf)}")
        self.log_output("------------------------")

    def log_output(self, message, end="\n"):
        # Put the message in the queue for the main thread to handle
        self.output_queue.put((message, end))

    def check_output_queue(self):
        # Process any pending output messages
        while not self.output_queue.empty():
            message, end = self.output_queue.get()
            self.output_display.config(state=tk.NORMAL)
            
            if end == "\n":
                # Add a new line
                if self.output_display.index('end-1c') != '1.0':  # If not empty
                    self.output_display.insert(tk.END, "\n")
                self.output_display.insert(tk.END, message)
            else:
                # Append without new line
                self.output_display.insert(tk.END, message)
            
            self.output_display.see(tk.END)  # Scroll to the end
            self.output_display.config(state=tk.DISABLED)
        
        # Check again after 100ms
        self.root.after(100, self.check_output_queue)

    def exit_app(self):
        # Set stop flag in case any thread is running
        self.stop_execution = True
        
        # Clean up temp directory
        try:
            if self.temp_dir.exists():
                for temp_file in self.temp_dir.glob("*"):
                    temp_file.unlink()
                self.temp_dir.rmdir()
        except:
            pass
        
        # Exit the application
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    # Create the main window
    root = tk.Tk()
    app = OllamaAITool(root)
    
    # Start the main loop
    root.mainloop()