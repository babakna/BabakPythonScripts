import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, font
import requests
import json
import time
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import sys

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
        self.verify_setup()

    def verify_setup(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")
            models_data = response.json().get("models", [])
            self.available_models = [model["name"] for model in models_data]
            if self.model not in self.available_models:
                print(f"Warning: Model {self.model} not found in available models.")
                print("Attempting to use default model llama2:latest")
                self.model = "llama2:latest"
        except Exception as e:
            raise Exception(f"Failed to verify Ollama setup: {str(e)}")

    def query_ollama(self, 
                    prompt: str, 
                    stream: bool = False,
                    context: List[str] = None) -> Optional[str] | Generator[str, None, None]:
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
                if stream:
                    return self._stream_response(url, data)
                else:
                    response = requests.post(url, json=data)
                    response.raise_for_status()
                    return response.json()["response"]
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
            similar_questions = [q.strip() for q in response.split('\n') if q.strip() and '?' in q][:3]
            return similar_questions
        return []

    def get_comprehensive_response(self, 
                                 original_question: str, 
                                 similar_questions: List[str],
                                 stream: bool = True) -> Optional[str] | Generator[str, None, None]:
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

class ChatbotGUI:
    def __init__(self, master):
        self.master = master
        master.title("Enhanced Ollama Chatbot")
        master.geometry("800x600")

        self.chatbot = OllamaChatbot()
        self.ollama_process = None
        self.is_processing = False
        self.current_context = None

        self.create_widgets()

    def create_widgets(self):
        self.frame = ttk.Frame(self.master, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        custom_font = font.Font(size=12)

        self.model_label = ttk.Label(self.frame, text="Select Model:", font=custom_font)
        self.model_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(self.frame, textvariable=self.model_var, values=self.chatbot.available_models, font=custom_font)
        self.model_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.model_dropdown.set(self.chatbot.model)

        self.query_label = ttk.Label(self.frame, text="Enter your query:", font=custom_font)
        self.query_label.grid(row=1, column=0, sticky=tk.W, pady=5)

        self.query_entry = ttk.Entry(self.frame, width=70, font=custom_font)
        self.query_entry.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.submit_button = ttk.Button(self.frame, text="Submit", command=self.process_query, style='Custom.TButton')
        self.submit_button.grid(row=2, column=2, sticky=tk.E, pady=5)

        self.status_label = ttk.Label(self.frame, text="Status:", font=custom_font)
        self.status_label.grid(row=3, column=0, sticky=tk.W, pady=5)

        self.status_text = scrolledtext.ScrolledText(self.frame, height=5, width=80, wrap=tk.WORD, font=custom_font)
        self.status_text.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.response_label = ttk.Label(self.frame, text="Response:", font=custom_font)
        self.response_label.grid(row=5, column=0, sticky=tk.W, pady=5)

        self.response_text = scrolledtext.ScrolledText(self.frame, height=15, width=80, wrap=tk.WORD, font=custom_font)
        self.response_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.clear_button = ttk.Button(self.frame, text="Clear", command=self.clear_output, style='Custom.TButton')
        self.clear_button.grid(row=7, column=0, sticky=tk.W, pady=5)

        self.test_button = ttk.Button(self.frame, text="Test", command=self.test_connection, style='Custom.TButton')
        self.test_button.grid(row=7, column=1, sticky=tk.W, pady=5)

        self.save_button = ttk.Button(self.frame, text="Save", command=self.save_output, style='Custom.TButton')
        self.save_button.grid(row=7, column=1, sticky=tk.E, pady=5)

        self.exit_button = ttk.Button(self.frame, text="Exit", command=self.exit_application, style='Custom.TButton')
        self.exit_button.grid(row=7, column=2, sticky=tk.E, pady=5)

        style = ttk.Style()
        style.configure('Custom.TButton', font=custom_font)

    def process_query(self):
        if self.is_processing:
            self.status_text.insert(tk.END, "Please wait for the current query to finish processing.\n")
            self.status_text.see(tk.END)
            return

        query = self.query_entry.get()
        if not query:
            self.status_text.insert(tk.END, "Please enter a query.\n")
            return

        self.chatbot.model = self.model_var.get()
        self.status_text.insert(tk.END, f"Processing query using model: {self.chatbot.model}...\n")
        self.status_text.see(tk.END)

        self.is_processing = True
        threading.Thread(target=self._process_query_thread, args=(query,), daemon=True).start()

    def _process_query_thread(self, query):
        try:
            similar_questions = self.chatbot.get_similar_questions(query)
            self.status_text.insert(tk.END, f"Generated {len(similar_questions)} similar questions:\n")
            for i, q in enumerate(similar_questions, 1):
                self.status_text.insert(tk.END, f"{i}. {q}\n")
            self.status_text.see(tk.END)
            self.master.update_idletasks()

            response = self.chatbot.get_comprehensive_response(query, similar_questions)
            if response:
                self.response_text.delete(1.0, tk.END)
                for chunk in response:
                    self.response_text.insert(tk.END, chunk)
                    self.response_text.see(tk.END)
                    self.master.update_idletasks()
                self.response_text.insert(tk.END, "\n*** FINISHED ***\n")
                self.response_text.insert(tk.END, "Please enter additional questions to continue.\n")
                self.response_text.see(tk.END)
                self.current_context = query  # Save the context for follow-up questions
            else:
                self.status_text.insert(tk.END, "No response generated. Please try again.\n")
        except Exception as e:
            self.status_text.insert(tk.END, f"Error: {str(e)}\n")
        finally:
            self.is_processing = False
            self.status_text.insert(tk.END, "Processing complete.\n")
            self.status_text.see(tk.END)
            self.master.update_idletasks()

    def clear_output(self):
        self.query_entry.delete(0, tk.END)
        self.status_text.delete(1.0, tk.END)
        self.response_text.delete(1.0, tk.END)
        self.current_context = None

    def save_output(self):
        with open("chatbot_output.txt", "w") as f:
            f.write("Query:\n")
            f.write(self.query_entry.get() + "\n\n")
            f.write("Status:\n")
            f.write(self.status_text.get(1.0, tk.END) + "\n")
            f.write("Response:\n")
            f.write(self.response_text.get(1.0, tk.END))
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

def start_ollama_serve():
    try:
        process = subprocess.Popen(["ollama", "serve"])
        time.sleep(5)  # Give Ollama some time to start
        return process
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return None

def main():
    ollama_process = start_ollama_serve()
    root = tk.Tk()
    gui = ChatbotGUI(root)
    gui.ollama_process = ollama_process
    root.mainloop()

if __name__ == "__main__":
    main()