import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, font, filedialog
import requests
import json
import time
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import sys
import socket
import os
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA

@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class OllamaChatbot:
    def __init__(self, 
                 model: str = "llama2:latest",
                 base_url: str = "http://localhost:11434",
                 max_retries: int = 3,
                 retry_delay: int = 1,
                 temperature: float = 0.7,
                 max_history: int = 10):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.temperature = temperature
        self.max_history = max_history
        self.conversation_history: List[ChatMessage] = []
        self.context = None  # Context array for maintaining conversation state
        self.vector_db = None  # Vector database for RAG
        self.verify_setup()

    def verify_setup(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")
            models_data = response.json().get("models", [])
            self.available_models = sorted([model["name"] for model in models_data], reverse=True)  # Sort models in descending order
            if self.model not in self.available_models:
                print(f"Warning: Model {self.model} not found in available models.")
                print("Attempting to use default model llama2:latest")
                self.model = "llama2:latest"
        except Exception as e:
            raise Exception(f"Failed to verify Ollama setup: {str(e)}")

    def query_ollama(self, 
                    prompt: str, 
                    stream: bool = False,
                    context: List[int] = None) -> Optional[Dict]:
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "temperature": self.temperature
        }
        if context:
            data["context"] = context
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=data)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"Error after {self.max_retries} attempts: {e}")
                    return None
                print(f"Attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

    def _stream_response(self, url: str, data: Dict) -> Generator[str, None, None]:
        with requests.post(url, json=data, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line)
                        yield json_response["response"]
                    except json.JSONDecodeError:
                        continue

    def get_similar_questions(self, user_input: str) -> List[str]:
        prompt = f"""Given the following question, generate 3 similar but different questions that are related to the same topic.
        Make the questions diverse but relevant.
        
        Original question: {user_input}
        
        Please provide only the questions, one per line."""
        response = self.query_ollama(prompt)
        if response:
            similar_questions = [q.strip() for q in response["response"].split('\n') if q.strip() and '?' in q][:3]
            return similar_questions
        return []

    def get_comprehensive_response(self, 
                                 original_question: str, 
                                 similar_questions: List[str],
                                 stream: bool = True) -> Optional[Dict]:
        context_prompt = f"""Consider the following main question and related questions:

        Main question: {original_question}

        Related questions:
        {chr(10).join('- ' + q for q in similar_questions)}... Please provide a comprehensive response that:
        1. Directly answers the main question
        2. Incorporates relevant insights from the related questions
        3. Maintains a coherent and well-structured flow
        4. Provides specific examples where appropriate"""
        return self.query_ollama(context_prompt, stream=stream)

    def add_to_history(self, role: str, content: str):
        self.conversation_history.append(ChatMessage(role=role, content=content))
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def load_files(self, file_paths: List[str]):
        """Load and process files into a vector database."""
        documents = []
        for file_path in file_paths:
            if file_path.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith(".docx"):
                loader = Docx2txtLoader(file_path)
            elif file_path.endswith(".xlsx"):
                loader = UnstructuredExcelLoader(file_path)
            else:
                print(f"Unsupported file type: {file_path}")
                continue
            documents.extend(loader.load())

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)

        # Create embeddings and vector database
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_db = Chroma.from_documents(texts, embeddings)

    def query_with_rag(self, query: str) -> Optional[str]:
        """Query the vector database and generate a response using RAG."""
        if not self.vector_db:
            return None
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.query_ollama,  # Use Ollama as the LLM
            chain_type="stuff",
            retriever=self.vector_db.as_retriever()
        )
        result = qa_chain.run(query)
        return result

class ChatbotGUI:
    def __init__(self, master):
        self.master = master
        master.title("Enhanced Ollama Chatbot with RAG")
        master.geometry("1000x900")  # Increased size for better visibility

        self.chatbot = OllamaChatbot()
        self.ollama_process = None
        self.is_processing = False
        self.stop_rendering = False  # Flag to stop rendering
        self.file_paths = []  # List to store uploaded file paths

        self.create_widgets()

    def create_widgets(self):
        self.frame = tk.Frame(self.master, padx=10, pady=10)
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        custom_font = font.Font(size=12)

        # Model selection
        self.model_label = tk.Label(self.frame, text="Select Model:", font=custom_font)
        self.model_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.model_var = tk.StringVar()
        self.model_dropdown = tk.OptionMenu(self.frame, self.model_var, *self.chatbot.available_models)
        self.model_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.model_var.set(self.chatbot.model)

        # File upload
        self.file_label = tk.Label(self.frame, text="Upload Files (PDF, Word, Excel):", font=custom_font)
        self.file_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.file_button = tk.Button(self.frame, text="Upload Files", command=self.upload_files, bg="light blue", font=custom_font)
        self.file_button.grid(row=1, column=1, sticky=tk.W, pady=5)

        # Query input
        self.query_label = tk.Label(self.frame, text="Enter your query:", font=custom_font)
        self.query_label.grid(row=2, column=0, sticky=tk.W, pady=5)

        self.query_entry = tk.Text(self.frame, height=3, width=90, wrap=tk.WORD, font=custom_font)
        self.query_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.submit_button = tk.Button(self.frame, text="Submit", command=self.process_query, bg="light blue", font=custom_font)
        self.submit_button.grid(row=3, column=2, sticky=tk.E, pady=5)

        # Follow-up input
        self.followup_label = tk.Label(self.frame, text="Enter any follow-up questions:", font=custom_font)
        self.followup_label.grid(row=4, column=0, sticky=tk.W, pady=5)

        self.followup_entry = tk.Text(self.frame, height=3, width=90, wrap=tk.WORD, font=custom_font)
        self.followup_entry.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # Status and response
        self.status_label = tk.Label(self.frame, text="Status:", font=custom_font)
        self.status_label.grid(row=6, column=0, sticky=tk.W, pady=5)

        self.status_text = scrolledtext.ScrolledText(self.frame, height=5, width=100, wrap=tk.WORD, font=custom_font)
        self.status_text.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.response_label = tk.Label(self.frame, text="Response:", font=custom_font)
        self.response_label.grid(row=8, column=0, sticky=tk.W, pady=5)

        self.response_text = scrolledtext.ScrolledText(self.frame, height=20, width=100, wrap=tk.WORD, font=custom_font)
        self.response_text.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # Buttons at the bottom
        self.button_frame = tk.Frame(self.frame)
        self.button_frame.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        self.clear_button = tk.Button(self.button_frame, text="Clear", command=self.clear_output, bg="white", font=custom_font)
        self.clear_button.grid(row=0, column=0, padx=5)

        self.save_button = tk.Button(self.button_frame, text="Save", command=self.save_output, bg="green", font=custom_font)
        self.save_button.grid(row=0, column=1, padx=5)

        self.stop_button = tk.Button(self.button_frame, text="Stop", command=self.stop_rendering_response, bg="orange", font=custom_font)
        self.stop_button.grid(row=0, column=2, padx=5)

        self.test_button = tk.Button(self.button_frame, text="Test", command=self.test_connection, bg="light blue", font=custom_font)
        self.test_button.grid(row=0, column=3, padx=5)

        self.display_button = tk.Button(self.button_frame, text="Display Entries", command=self.display_entries, bg="yellow", font=custom_font)
        self.display_button.grid(row=0, column=4, padx=5)

        self.exit_button = tk.Button(self.button_frame, text="Exit", command=self.exit_application, bg="red", font=custom_font)
        self.exit_button.grid(row=0, column=5, padx=5)

    def upload_files(self):
        """Allow the user to upload files."""
        file_paths = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("PDF Files", "*.pdf"), ("Word Files", "*.docx"), ("Excel Files", "*.xlsx")]
        )
        if file_paths:
            self.file_paths = list(file_paths)
            self.status_text.insert(tk.END, f"Uploaded {len(self.file_paths)} files.\n")
            self.status_text.see(tk.END)

    def display_entries(self):
        """Display the uploaded file entries."""
        if not self.file_paths:
            self.status_text.insert(tk.END, "No files uploaded.\n")
            return
        self.status_text.insert(tk.END, "Uploaded Files:\n")
        for i, file_path in enumerate(self.file_paths, 1):
            self.status_text.insert(tk.END, f"{i}. {os.path.basename(file_path)}\n")
        self.status_text.see(tk.END)

    def process_query(self):
        if self.is_processing:
            self.status_text.insert(tk.END, "Please wait for the current query to finish processing.\n")
            self.status_text.see(tk.END)
            return

        query = self.query_entry.get("1.0", tk.END).strip()
        followup_query = self.followup_entry.get("1.0", tk.END).strip()

        if not query and not followup_query:
            self.status_text.insert(tk.END, "Please enter a query or follow-up question.\n")
            return

        # Use follow-up query if available, otherwise use the original query
        if followup_query:
            query = followup_query
            self.status_text.insert(tk.END, f"Processing follow-up question: {query}\n")
        else:
            self.status_text.insert(tk.END, f"Processing new query: {query}\n")

        self.chatbot.model = self.model_var.get()
        self.status_text.insert(tk.END, f"Using model: {self.chatbot.model}...\n")
        self.status_text.see(tk.END)

        self.is_processing = True
        self.stop_rendering = False  # Reset stop flag
        threading.Thread(target=self._process_query_thread, args=(query,), daemon=True).start()

    def _process_query_thread(self, query):
        try:
            if self.file_paths:
                # Load files into the vector database if not already loaded
                if not self.chatbot.vector_db:
                    self.status_text.insert(tk.END, "Loading files into vector database...\n")
                    self.status_text.see(tk.END)
                    self.chatbot.load_files(self.file_paths)
                    self.status_text.insert(tk.END, "Files loaded successfully.\n")
                    self.status_text.see(tk.END)

                # Query with RAG
                response = self.chatbot.query_with_rag(query)
            else:
                # Query without RAG
                response = self.chatbot.query_ollama(query)

            if response:
                self.response_text.delete("1.0", tk.END)
                self.response_text.insert(tk.END, response)
                self.response_text.see(tk.END)
                self.master.update_idletasks()

                # Add to conversation history
                self.chatbot.add_to_history("user", query)
                self.chatbot.add_to_history("assistant", response)
            else:
                self.status_text.insert(tk.END, "No response generated. Please try again.\n")
        except Exception as e:
            self.status_text.insert(tk.END, f"Error: {str(e)}\n")
        finally:
            self.is_processing = False
            self.status_text.insert(tk.END, "Processing complete.\n")
            self.status_text.see(tk.END)
            self.master.update_idletasks()

    def stop_rendering_response(self):
        """Stop rendering the response in the Response text widget."""
        self.stop_rendering = True
        self.status_text.insert(tk.END, "Response rendering stopped by user.\n")
        self.status_text.see(tk.END)

    def clear_output(self):
        self.query_entry.delete("1.0", tk.END)
        self.followup_entry.delete("1.0", tk.END)
        self.status_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        self.file_paths = []  # Clear uploaded files
        self.chatbot.context = None  # Reset context
        self.chatbot.conversation_history.clear()  # Clear conversation history
        self.chatbot.vector_db = None  # Reset vector database

    def save_output(self):
        with open("chatbot_output.txt", "w") as f:
            f.write("Query:\n")
            f.write(self.query_entry.get("1.0", tk.END).strip() + "\n\n")
            f.write("Follow-up Query:\n")
            f.write(self.followup_entry.get("1.0", tk.END).strip() + "\n\n")
            f.write("Status:\n")
            f.write(self.status_text.get("1.0", tk.END).strip() + "\n")
            f.write("Response:\n")
            f.write(self.response_text.get("1.0", tk.END).strip())
        self.status_text.insert(tk.END, "Output saved to chatbot_output.txt\n")

    def test_connection(self):
        try:
            self.chatbot.verify_setup()
            self.status_text.insert(tk.END, "Connection test successful. Ollama is running and accessible.\n")
            self.status_text.insert(tk.END, f"Available models: {', '.join(self.chatbot.available_models)}\n")
            self.status_text.insert(tk.END, f"Current model: {self.chatbot.model}\n")
            self.status_text.insert(tk.END, f"Ollama server URL: {self.chatbot.base_url}\n")
        except Exception as e:
            self.status_text.insert(tk.END, f"Connection test failed: {str(e)}\n")
        self.status_text.see(tk.END)

    def exit_application(self):
        if self.ollama_process:
            self.ollama_process.terminate()
            self.ollama_process.wait()
        self.master.quit()

def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_ollama_serve():
    try:
        if is_port_in_use(11434):
            print("Ollama server is already running.")
            return None
        process = subprocess.Popen(["ollama", "serve"])
        time.sleep(5)  # Give Ollama some time to start
        return process
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return None

def main():
    ollama_process = start_ollama_serve()
    if ollama_process is None:
        print("Failed to start Ollama server. Please ensure Ollama is installed and running.")
    root = tk.Tk()
    gui = ChatbotGUI(root)
    gui.ollama_process = ollama_process
    root.mainloop()

if __name__ == "__main__":
    main()