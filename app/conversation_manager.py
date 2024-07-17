# conversation_manager.py
import json
import logging
from datetime import datetime

class ConversationContext:
    def __init__(self):
        self.current_topic = None
        self.topic_messages = []
        self.repeat_count = 0  # Aggiungiamo questo contatore

    def set_topic(self, topic):
        if self.current_topic == topic:
            self.repeat_count += 1
        else:
            self.repeat_count = 0
        self.current_topic = topic
        if self.repeat_count >= 3:
            self.topic_messages = []
            self.repeat_count = 0

    def add_message(self, message):
        self.topic_messages.append(message)

    def get_context(self):
        return {
            "topic": self.current_topic,
            "messages": self.topic_messages,
            "repeat_count": self.repeat_count
        }

    def clear(self):
        self.current_topic = None
        self.topic_messages = []
        self.repeat_count = 0

class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.failed_attempts = {}

    def add_message(self, user_name, message, is_user):
        if user_name not in self.conversations:
            self.conversations[user_name] = []
        self.conversations[user_name].append({"content": message, "is_user": is_user})
        
        if user_name not in self.failed_attempts:
            self.failed_attempts[user_name] = 0

    def get_conversation(self, user_name):
        return self.conversations.get(user_name, [])

    def clear_conversation(self, user_name):
        if user_name in self.conversations:
            del self.conversations[user_name]
        if user_name in self.failed_attempts:
            del self.failed_attempts[user_name]

    def increment_failed_attempts(self, user_name):
        current_attempts = self.failed_attempts.get(user_name, 0)
        self.failed_attempts[user_name] = current_attempts + 1
        
    def get_failed_attempts(self, user_name):
        return self.failed_attempts.get(user_name, 0)

    def reset_failed_attempts(self, user_name):
        self.failed_attempts[user_name] = 0

    # Nuovi metodi per gestire il contesto
    def set_context(self, user_name, topic):
        if user_name not in self.conversations:
            self.conversations[user_name] = []
        if not hasattr(self, 'contexts'):
            self.contexts = {}
        if user_name not in self.contexts:
            self.contexts[user_name] = ConversationContext()
        
        self.contexts[user_name].set_topic(topic)
        
        # Se il contesto è stato ripetuto 3 volte, lo svuotiamo
        if self.contexts[user_name].repeat_count >= 3:
            self.clear_context_messages(user_name)
            logging.info(f"Utente {user_name}: History del contesto svuotata dopo 3 ripetizioni")
			
    def add_context_message(self, user_name, message):
        if hasattr(self, 'contexts') and user_name in self.contexts:
            self.contexts[user_name].add_message(message)

    def get_context(self, user_name):
        if hasattr(self, 'contexts') and user_name in self.contexts:
            return self.contexts[user_name].get_context()
        return None

    def clear_context(self, user_name):
        if hasattr(self, 'contexts') and user_name in self.contexts:
            self.contexts[user_name].clear()

    def clear_context_messages(self, user_name):
        if user_name in self.contexts:
           self.contexts[user_name].topic_messages = []

    def get_context_repeat_count(self, user_name):
        if hasattr(self, 'contexts') and user_name in self.contexts:
            return self.contexts[user_name].repeat_count
        return 0		   