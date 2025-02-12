import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, font, filedialog
import requests
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import sys
import os
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import Ollama

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
                 model: str = "llama2",
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
        self.vector_db = None
        self.verify_setup()

    def verify_setup(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")
            models_data = response.json().get("models", [])
            self.available_models = sorted([model["name"] for model in models_data], reverse=True)
            if self.model not in self.available_models:
                print(f"Warning: Model {self.model} not found in available models.")
                print("Attempting to use default model llama2")
                self.model = "llama2"
        except Exception as e:
            raise Exception(f"Failed to verify Ollama setup: {str(e)}")

    def load_files(self, file_paths: List[str]):
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

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
        self.vector_db = Chroma.from_documents(texts, embeddings)

    def query_with_rag(self, query: str) -> Optional[str]:
        if not self.vector_db:
            return None

        llm = Ollama(model=self.model, temperature=self.temperature)
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=self.vector_db.as_retriever()
        )
        result = qa_chain.run(query)
        return result

class ChatbotGUI:
    def __init__(self, master):
        self.master = master
        master.title("RAG Chatbot with Ollama")
        master.geometry("1000x800")

        self.chatbot = OllamaChatbot()
        self.ollama_process = None
        self.is_processing = False
        self.file_paths = []

        self.create_widgets()

    def create_widgets(self):
        self.frame = tk.Frame(self.master, padx=10, pady=10)
        self.frame.pack(fill=tk.BOTH, expand=True)

        custom_font = font.Font(size=12)

        # Model selection
        self.model_label = tk.Label(self.frame, text="Select Model:", font=custom_font)
        self.model_label.pack(anchor=tk.W, pady=5)

        self.model_var = tk.StringVar()
        self.model_dropdown = tk.OptionMenu(self.frame, self.model_var, *self.chatbot.available_models)
        self.model_dropdown.pack(fill=tk.X, pady=5)
        self.model_var.set(self.chatbot.model)

        # File upload
        self.file_button = tk.Button(self.frame, text="Upload Files", command=self.upload_files, bg="light blue",
                                     font=custom_font)
        self.file_button.pack(fill=tk.X, pady=5)

        # Query input
        self.query_label = tk.Label(self.frame, text="Enter your query:", font=custom_font)
        self.query_label.pack(anchor=tk.W, pady=5)
        self.query_entry = tk.Text(self.frame, height=3, wrap=tk.WORD, font=custom_font)
        self.query_entry.pack(fill=tk.X, pady=5)

        self.submit_button = tk.Button(self.frame, text="Submit", command=self.process_query, bg="light green",
                                       font=custom_font)
        self.submit_button.pack(fill=tk.X, pady=5)

        # Response
        self.response_label = tk.Label(self.frame, text="Response:", font=custom_font)
        self.response_label.pack(anchor=tk.W, pady=5)

        self.response_text = scrolledtext.ScrolledText(self.frame, height=20, wrap=tk.WORD, font=custom_font)
        self.response_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Buttons at the bottom
        self.button_frame = tk.Frame(self.frame)
        self.button_frame.pack(fill=tk.X, pady=10)

        self.test_button = tk.Button(self.button_frame, text="Test Connection", command=self.test_connection,
                                     bg="light blue", font=custom_font)
        self.test_button.pack(side=tk.LEFT, padx=5)

        self.exit_button = tk.Button(self.button_frame, text="Exit", command=self.exit_application, bg="red",
                                     font=custom_font)
        self.exit_button.pack(side=tk.RIGHT, padx=5)

        self.clear_button = tk.Button(self.button_frame, text="Clear Display", command=self.clear_display, bg="white",
                                      font=custom_font)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.display_docs_button = tk.Button(self.button_frame, text="Display Uploaded Documents",
                                             command=self.display_uploaded_documents, bg="yellow", font=custom_font)
        self.display_docs_button.pack(side=tk.LEFT, padx=5)

    def upload_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("PDF Files", "*.pdf"), ("Word Files", "*.docx"), ("Excel Files", "*.xlsx")]
        )
        if file_paths:
            self.file_paths.extend(file_paths)
            # Display uploaded files in response text
            self.response_text.insert(tk.END, f"Uploaded {len(file_paths)} files.\n")
            self.response_text.see(tk.END)

    def process_query(self):
        if self.is_processing:
            self.response_text.insert(tk.END, "Please wait for the current query to finish processing.\n")
            self.response_text.see(tk.END)
            return

        query = self.query_entry.get("1.0", tk.END).strip()

        if not query:
            self.response_text.insert(tk.END, "Please enter a query.\n")
            self.response_text.see(tk.END)
            return

        self.chatbot.model = self.model_var.get()
        self.response_text.insert(tk.END, f"Using model: {self.chatbot.model}...\n")
        self.response_text.see(tk.END)

        self.is_processing = True
        threading.Thread(target=self._process_query_thread, args=(query,), daemon=True).start()

    def _process_query_thread(self, query):
        try:
            if self.file_paths:
                self.response_text.insert(tk.END, "Loading files into vector database...\n")
                self.response_text.see(tk.END)
                self.chatbot.load_files(self.file_paths)
                self.response_text.insert(tk.END, "Files loaded successfully.\n")
                self.response_text.see(tk.END)

                response = self.chatbot.query_with_rag(query)
            else:
                response = "No files uploaded. Please upload files before querying."

            if response:
                self.response_text.insert(tk.END, f"Response: {response}\n")
                self.response_text.see(tk.END)
        except Exception as e:
            self.response_text.insert(tk.END, f"Error processing query: {e}\n")
            self.response_text.see(tk.END)
        finally:
            self.is_processing = False

    def test_connection(self):
        try:
            response = requests.get(f"{self.chatbot.base_url}/api/tags")
            if response.status_code == 200:
                message = "Connection to Ollama server is successful.\n"
            else:
                message = f"Failed to connect to Ollama server. Status code: {response.status_code}\n"
                self.start_ollama_serve()
        except requests.exceptions.RequestException as e:
            message = f"Failed to connect to Ollama server: {e}\n"
            self.start_ollama_serve()

        # Display test results in response_text
        self.response_text.insert(tk.END, message)
        self.response_text.see(tk.END)

    def start_ollama_serve(self):
        try:
            subprocess.Popen(["ollama", "serve"])
            message = "Ollama server started successfully. Please wait a moment and try again.\n"
        except Exception as e:
            message = f"Failed to start Ollama server: {e}\n"

        self.response_text.insert(tk.END, message)
        self.response_text.see(tk.END)

    def clear_display(self):
        self.response_text.delete("1.0", tk.END)

    def display_uploaded_documents(self):
        if not self.file_paths:
            self.response_text.insert(tk.END, "No files uploaded.\n")
            self.response_text.see(tk.END)
            return

        self.response_text.insert(tk.END, "Uploaded Documents:\n")
        for i, path in enumerate(self.file_paths, 1):
            filename = os.path.basename(path)
            self.response_text.insert(tk.END, f"{i}. {filename}\n")
        self.response_text.see(tk.END)

    def exit_application(self):
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChatbotGUI(root)
    root.mainloop()
