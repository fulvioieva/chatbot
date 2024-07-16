# followup_manager.py
import json
from datetime import datetime

class FollowUpManager:
    def __init__(self, file_path='followup_list.json'):
        self.file_path = file_path
        self.followup_list = self.load_list()

    def load_list(self):
        try:
            with open(self.file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_list(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.followup_list, file, indent=2)

    def add_to_followup(self, user_name, issue):
        self.followup_list.append({
            "name": user_name,
            "issue": issue,
            "timestamp": datetime.now().isoformat()
        })
        self.save_list()

    def get_followup_list(self):
        return [item['name'] for item in self.followup_list]

    def remove_from_followup(self, user_name):
        self.followup_list = [item for item in self.followup_list if item['name'] != user_name]
        self.save_list()
