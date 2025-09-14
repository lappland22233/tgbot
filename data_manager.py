import json
import os
from pathlib import Path

class DataManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.admin_file = self.data_dir / "admins.json"
        self.group_file = self.data_dir / "groups.json"
        self.prompt_file = self.data_dir / "prompts.json"
        self.keyword_file = self.data_dir / "keywords.json"
        self.model_file = self.data_dir / "models.json"
        
        self._init_files()
        
    def _init_files(self):
        for file in [self.admin_file, self.group_file, 
                    self.prompt_file, self.keyword_file, self.model_file]:
            if not file.exists():
                with open(file, 'w') as f:
                    json.dump([], f)
    
    def load_data(self, file):
        with open(file, 'r') as f:
            return json.load(f)
            
    def save_data(self, file, data):
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)
            
    # 管理员管理方法
    def add_admin(self, user_id):
        admins = self.load_data(self.admin_file)
        if user_id not in admins:
            admins.append(user_id)
            self.save_data(self.admin_file, admins)
            return True
        return False
        
    def remove_admin(self, index):
        admins = self.load_data(self.admin_file)
        if 0 <= index < len(admins):
            admins.pop(index)
            self.save_data(self.admin_file, admins)
            return True
        return False
        
    # 群组管理方法
    def deauthorize_group(self, group_id):
        groups = self.load_data(self.group_file)
        if group_id in groups:
            groups.remove(group_id)
            self.save_data(self.group_file, groups)
            return True
        return False
        
    # 提示词管理方法
    def get_prompts(self):
        return self.load_data(self.prompt_file)
        
    def remove_prompt(self, index):
        prompts = self.load_data(self.prompt_file)
        if 0 <= index < len(prompts):
            prompts.pop(index)
            self.save_data(self.prompt_file, prompts)
            return True
        return False
        
    # 关键词管理方法
    def add_keyword(self, keyword, response):
        keywords = self.load_data(self.keyword_file)
        keywords.append({"keyword": keyword, "response": response})
        self.save_data(self.keyword_file, keywords)
        return True
        
    def get_keywords(self):
        return self.load_data(self.keyword_file)
        
    # 模型管理方法
    def add_model(self, model_name):
        models = self.load_data(self.model_file)
        if model_name not in models:
            models.append(model_name)
            self.save_data(self.model_file, models)
            return True
        return False
        
    def get_models(self):
        return self.load_data(self.model_file)