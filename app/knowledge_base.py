import json
import csv
import os
from datetime import datetime, timedelta

class KnowledgeBase:
    def __init__(self, directory):
        self.directory = directory
        self.data = {}
        self.last_update = None
        self.update_interval = timedelta(hours=1)

    def load_data(self):
        current_time = datetime.now()
        if self.last_update is None or current_time - self.last_update > self.update_interval:
            self.data = {}
            for filename in os.listdir(self.directory):
                filepath = os.path.join(self.directory, filename)
                if filename.endswith('.json'):
                    with open(filepath, 'r') as f:
                        self.data[filename[:-5]] = json.load(f)
                elif filename.endswith('.csv'):
                    with open(filepath, 'r') as f:
                        reader = csv.DictReader(f)
                        self.data[filename[:-4]] = list(reader)
            self.last_update = current_time

    def get_relevant_info(self, query):
        self.load_data()
        relevant_info = []
        for key, value in self.data.items():
            if isinstance(value, list):
                relevant_info.extend([item for item in value if query.lower() in str(item).lower()])
            elif isinstance(value, dict):
                relevant_info.extend([v for k, v in value.items() if query.lower() in k.lower() or query.lower() in str(v).lower()])
        return relevant_info