# conversation_manager.py
import json
from datetime import datetime

class ConversationContext:
    def __init__(self):
        self.current_topic = None
        self.topic_messages = []

    def set_topic(self, topic):
        self.current_topic = topic
        self.topic_messages = []

    def add_message(self, message):
        self.topic_messages.append(message)

    def get_context(self):
        return {
            "topic": self.current_topic,
            "messages": self.topic_messages
        }

    def clear(self):
        self.current_topic = None
        self.topic_messages = []

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
        self.failed_attempts[user_name] = self.failed_attempts.get(user_name, 0) + 1

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