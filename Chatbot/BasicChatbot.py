import requests
import json
import time
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import sys

# README
# install if not present: pip install requests dataclasses
# Ensure ollama is running the following in a terminal: ollama serve
# 


@dataclass
class ChatMessage:
    """
    Data class to store chat messages
    """
    role: str
    content: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class OllamaChatbot:
    def __init__(self, 
                 model: str = "llama2:latest",  # Updated to use exact model name
                 base_url: str = "http://localhost:11434",
                 max_retries: int = 3,
                 retry_delay: int = 1,
                 temperature: float = 0.7,
                 max_history: int = 10):
        """
        Initialize the chatbot with customizable parameters
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.temperature = temperature
        self.max_history = max_history
        self.conversation_history: List[ChatMessage] = []

        # Verify server and model on startup
        self.verify_setup()

    def verify_setup(self):
        """
        Verify server connection and model availability
        """
        try:
            # Check server
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise Exception(f"Server returned status code: {response.status_code}")

            # Get available models
            models_data = response.json().get("models", [])
            available_models = [model["name"] for model in models_data]
            
            print(f"Available models: {available_models}")
            
            if self.model not in available_models:
                print(f"Warning: Model {self.model} not found in available models.")
                print("Attempting to use default model llama2:latest")
                self.model = "llama2:latest"

        except Exception as e:
            raise Exception(f"Failed to verify Ollama setup: {str(e)}")

    def query_ollama(self, 
                    prompt: str, 
                    stream: bool = False,
                    context: List[str] = None) -> Optional[str] | Generator[str, None, None]:
        """
        Send a query to Ollama with enhanced error handling
        """
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
        """
        Stream the response from Ollama
        """
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
        """
        Generate similar questions based on user input
        """
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
        """
        Generate a comprehensive response using original and similar questions
        """
        context_prompt = f"""Consider the following main question and related questions:

        Main question: {original_question}

        Related questions:
        {chr(10).join('- ' + q for q in similar_questions)}

        Please provide a comprehensive response that:
        1. Directly answers the main question
        2. Incorporates relevant insights from the related questions
        3. Maintains a coherent and well-structured flow
        4. Provides specific examples where appropriate"""
        
        return self.query_ollama(context_prompt, stream=stream)

    def add_to_history(self, role: str, content: str):
        """
        Add a message to conversation history
        """
        self.conversation_history.append(ChatMessage(role=role, content=content))
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

def main():
    """
    Main function to run the chatbot
    """
    print("Initializing Enhanced Ollama Chatbot...")
    
    try:
        chatbot = OllamaChatbot()  # Uses llama2:latest by default
    except Exception as e:
        print(f"Error initializing chatbot: {e}")
        print("\nPlease ensure:")
        print("1. Ollama is running (run 'ollama serve')")
        print("2. The model is available (run 'ollama list')")
        sys.exit(1)

    print("\nChatbot initialized successfully!")
    print("=" * 50)
    print("Features:")
    print("- Streaming responses")
    print("- Similar question generation")
    print("- Conversation history")
    print("\nType 'quit' to exit, 'history' to see conversation history")
    
    while True:
        try:
            user_input = input("\nYour question: ").strip()
            
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
                
            if user_input.lower() == 'history':
                print("\nConversation History:")
                for msg in chatbot.conversation_history:
                    print(f"{msg.timestamp.strftime('%H:%M:%S')} - {msg.role}: {msg.content[:100]}...")
                continue
            
            if not user_input:
                print("Please enter a valid question.")
                continue
            
            chatbot.add_to_history('user', user_input)
            
            print("\nProcessing your question...")
            
            similar_questions = chatbot.get_similar_questions(user_input)
            if not similar_questions:
                print("Using only original question.")
                response = chatbot.query_ollama(user_input, stream=True)
            else:
                print("\nConsidering these related questions:")
                for i, q in enumerate(similar_questions, 1):
                    print(f"{i}. {q}")
                
                print("\nResponse:")
                response = chatbot.get_comprehensive_response(user_input, similar_questions)
            
            if response:
                full_response = ""
                try:
                    for chunk in response:
                        print(chunk, end='', flush=True)
                        full_response += chunk
                    print()
                    chatbot.add_to_history('assistant', full_response)
                except Exception as e:
                    print(f"\nError during response streaming: {e}")
            else:
                print("Sorry, I couldn't generate a response. Please try again.")

        except KeyboardInterrupt:
            print("\nExiting gracefully...")
            break

        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            continue

if __name__ == "__main__":
    main()