# conversation_manager.py
import json
from datetime import datetime

class ConversationManager:
    def __init__(self, file_path='conversations.json'):
        self.file_path = file_path
        self.conversations = self.load_conversations()

    def load_conversations(self):
        try:
            with open(self.file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_conversations(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.conversations, file, indent=2)

    def add_message(self, user_name, message, is_user=True):
        if user_name not in self.conversations:
            self.conversations[user_name] = []
        
        self.conversations[user_name].append({
            "timestamp": datetime.now().isoformat(),
            "content": message,
            "is_user": is_user
        })
        self.save_conversations()

    def get_conversation(self, user_name):
        return self.conversations.get(user_name, [])

    def clear_conversation(self, user_name):
        if user_name in self.conversations:
            del self.conversations[user_name]
            self.save_conversations()
