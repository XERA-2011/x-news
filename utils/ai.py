# ai.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

load_dotenv()

# 可用的Gemini模型列表
AVAILABLE_MODELS = {
    # ================ 1.5 系列模型 ================
    # Flash 模型 (更快速)
    "gemini-1.5-flash-latest": {
        "description": "1.5 Flash 模型的最新版本，更快速，适合一般问答",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash": {
        "description": "1.5 Flash 基础模型",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-001": {
        "description": "1.5 Flash 的 001 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-002": {
        "description": "1.5 Flash 的 002 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-8b": {
        "description": "1.5 Flash 8B 小型模型",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-flash-8b-latest": {
        "description": "1.5 Flash 8B 模型的最新版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    
    # Pro 模型 (更强大)
    "gemini-1.5-pro-latest": {
        "description": "1.5 Pro 模型的最新版本，更强大的推理能力",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-pro": {
        "description": "1.5 Pro 基础模型",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-pro-001": {
        "description": "1.5 Pro 的 001 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-1.5-pro-002": {
        "description": "1.5 Pro 的 002 版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    
    # ================ 2.5 系列模型 (预览版) ================
    "gemini-2.5-flash-preview-05-20": {
        "description": "2.5 Flash 最新预览版本 (2025-05-20)",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-2.5-pro-preview-05-06": {
        "description": "2.5 Pro 最新预览版本 (2025-05-06)",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-2.5-flash-preview-tts": {
        "description": "2.5 Flash 支持文本转语音的预览版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    "gemini-2.5-pro-preview-tts": {
        "description": "2.5 Pro 支持文本转语音的预览版本",
        "max_tokens": 8192,
        "supports_tools": True
    },
    
    # ================ 1.0 系列模型 ================
    "gemini-pro": {
        "description": "Gemini 1.0 Pro 模型，支持文本处理",
        "max_tokens": 2048,
        "supports_tools": True
    },
    "gemini-pro-vision": {
        "description": "Gemini 1.0 Pro Vision 模型，支持图像处理",
        "max_tokens": 2048,
        "supports_tools": False
    },
    
    # ================ 嵌入模型 ================
    "embedding-gecko-001": {
        "description": "PaLM 2 嵌入模型",
        "max_tokens": 768,  # 嵌入维度
        "supports_tools": False
    },
    "gemini-embedding-exp": {
        "description": "Gemini 嵌入模型（实验版）",
        "max_tokens": 768,  # 嵌入维度可能更高
        "supports_tools": False
    },
}

class GeminiAI:
    def __init__(self, api_key=None):
        """
        Initialize the GeminiAI class
        
        Args:
            api_key (str, optional): Gemini API key. If not provided, will try to get from environment variable.
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key is required. Please provide it or set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        
        # Default safety settings
        self.safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
        ]
        
        # Default generation config
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 60,
            "max_output_tokens": 8192,
        }

    def get_available_models(self):
        """
        Get all available models from the API
        
        Returns:
            dict: Dictionary of available models categorized by type
        """
        try:
            all_models = genai.list_models()
            
            model_by_type = {
                "text": [],
                "chat": [],
                "embedding": [],
                "multimodal": [],
                "other": []
            }
            
            for model in all_models:
                model_name = model.name
                short_name = model_name.split('/')[-1] if '/' in model_name else model_name
                
                if "embedding" in short_name:
                    model_by_type["embedding"].append(short_name)
                elif "vision" in short_name or "multimodal" in short_name:
                    model_by_type["multimodal"].append(short_name)
                elif "chat" in short_name:
                    model_by_type["chat"].append(short_name)
                elif any(text_id in short_name for text_id in ["gemini", "pro", "flash", "bison"]):
                    model_by_type["text"].append(short_name)
                else:
                    model_by_type["other"].append(short_name)
            
            return model_by_type
            
        except Exception as e:
            print(f"Failed to get model list: {str(e)}")
            return {}

    def list_models(self):
        """Print all available models"""
        model_by_type = self.get_available_models()
        
        if not any(model_by_type.values()):
            print("No models found or API call failed")
            return
        
        print("\nAvailable Models:")
        print("-" * 80)
        
        for model_type, models in model_by_type.items():
            if models:
                print(f"\n{model_type.title()} Models:")
                for model in sorted(models):
                    print(f"- {model}")
        
        print("\n" + "-" * 80)

    def ask(self, prompt, model_name="gemini-1.5-flash-latest", max_output_tokens=None, stream=True):
        """
        Ask a question to the AI model
        
        Args:
            prompt (str): The question to ask
            model_name (str, optional): Model name to use. Defaults to "gemini-1.5-flash-latest"
            max_output_tokens (int, optional): Maximum output tokens. If not specified, will use model's default
            stream (bool, optional): Whether to stream the response. Defaults to True
            
        Returns:
            str: The AI's response
        """
        try:
            # Get model info
            model_info = AVAILABLE_MODELS.get(model_name, {
                "description": "Unknown model",
                "max_tokens": 8192,
                "supports_tools": True
            })
            
            # Update generation config
            if max_output_tokens:
                self.generation_config["max_output_tokens"] = max_output_tokens
            else:
                self.generation_config["max_output_tokens"] = model_info["max_tokens"]
            
            # Create model instance
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            print(f"Using model: {model_name} - {model_info['description']}")
            print(f"Max output tokens: {self.generation_config['max_output_tokens']}")
            # print(f"\n🤖 Question: {prompt}") # 提示词可能超级长，这里不打印显示
            print("-" * 80)
            
            # Generate response
            response = model.generate_content(
                prompt,
                stream=stream
            )
            
            if stream:
                full_response = ""
                for chunk in response:
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        full_response += chunk.text
                print("\n" + "-" * 80)
                return full_response
            else:
                return response.text
            
        except Exception as e:
            print(f"AI response failed: {str(e)}")
            return None

def ask_ai(prompt, model_name="gemini-1.5-flash-latest", max_output_tokens=None, stream=True):
    """
    Convenience function to ask AI a question
    
    Args:
        prompt (str): The question to ask
        model_name (str, optional): Model name to use. Defaults to "gemini-1.5-flash-latest"
        max_output_tokens (int, optional): Maximum output tokens
        stream (bool, optional): Whether to stream the response. Defaults to True
        
    Returns:
        str: The AI's response
    """
    ai = GeminiAI()
    return ai.ask(prompt, model_name, max_output_tokens, stream)

if __name__ == "__main__":
    # Example usage
    ai = GeminiAI()
    ai.list_models()
    
    # Example question
    response = ai.ask("What is the capital of France?")