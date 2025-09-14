import os
import configparser
from pathlib import Path

class Config:
    def __init__(self):
        self.config_file = Path("config.ini")
        self.config = configparser.ConfigParser()
        
        if not self.config_file.exists():
            self._setup_config()
        else:
            self.config.read(self.config_file)
            
    def _setup_config(self):
        print("首次运行，请完成配置:")
        self.config['DEFAULT'] = {
            'telegram_token': input("请输入Telegram Bot Token: "),
            'admin_id': input("请输入主管理员ID: "),
            'ai_api_key': input("请输入AI API Key: "),
            'ai_base_url': "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
            
    @property
    def telegram_token(self):
        return self.config['DEFAULT']['telegram_token']
        
    @property
    def admin_id(self):
        return int(self.config['DEFAULT']['admin_id'])
        
    @property
    def ai_api_key(self):
        return self.config['DEFAULT']['ai_api_key']
        
    @property
    def ai_base_url(self):
        return self.config['DEFAULT']['ai_base_url']