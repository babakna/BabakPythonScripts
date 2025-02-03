# First, let's create a simple test script to verify everything before running the main chatbot
import requests
import json
import sys

def test_ollama_setup():
    """
    Test Ollama setup and model availability
    Returns tuple of (is_success, message)
    """
    print("Testing Ollama setup...")
    
    # 1. Test server connection
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code != 200:
            return False, "Ollama server responded with status code: " + str(response.status_code)
    except requests.exceptions.RequestException as e:
        return False, f"Could not connect to Ollama server: {str(e)}"

    # 2. Get available models
    try:
        response = requests.get("http://localhost:11434/api/tags")
        available_models = []
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            available_models = [model["name"] for model in models_data]
            print(f"Available models: {available_models}")
    except Exception as e:
        return False, f"Error getting model list: {str(e)}"

    # 3. Test specific model
    test_prompt = "Hello, how are you?"
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": test_prompt
            }
        )
        if response.status_code == 200:
            return True, "Ollama is working correctly with llama2 model"
        else:
            return False, f"Error with model response: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return False, f"Error testing model: {str(e)}"

if __name__ == "__main__":
    success, message = test_ollama_setup()
    print("\nTest Results:")
    print("Status:", "Success" if success else "Failed")
    print("Message:", message)
    
    if not success:
        print("\nTroubleshooting steps:")
        print("1. Verify Ollama is running:")
        print("   - Run 'ollama serve' in a new terminal")
        print("\n2. Check available models:")
        print("   - Run 'ollama list' in a terminal")
        print("\n3. If llama2 is not listed, pull it:")
        print("   - Run 'ollama pull llama2'")
        print("\n4. If problems persist, try:")
        print("   - Stop Ollama (find process and end it in Task Manager)")
        print("   - Start Ollama again with 'ollama serve'")




