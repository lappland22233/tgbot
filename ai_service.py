import os
from openai import OpenAI
from config import Config

class AIService:
    def __init__(self):
        self.config = Config()
        self.client = OpenAI(
            api_key=self.config.ai_api_key,
            base_url=self.config.ai_base_url
        )
        self.current_model = "qwen-plus"
        
    async def chat_completion(self, messages, user_name=None):
        if user_name:
            system_msg = next((msg for msg in messages if msg['role'] == 'system'), None)
            if system_msg:
                system_msg['content'] += f"\n当前用户: {user_name}"
        
        completion = self.client.chat.completions.create(
            model=self.current_model,
            messages=messages
        )
        return completion.choices[0].message.content
        
    def set_model(self, model):
        self.current_model = model