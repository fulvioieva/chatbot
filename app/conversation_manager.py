# conversation_manager.py
import json
import logging

class ConversationContext:
    def __init__(self, topic):
        self.topic = topic
        self.messages = []
        self.repeat_count = 0

    def set_topic(self, topic):
        if self.topic == topic:
            self.repeat_count += 1
        else:
            self.repeat_count = 0
        self.topic = topic
        if self.repeat_count >= 3:
            self.topic_messages = []
            self.repeat_count = 0

    def add_message(self, message):
        self.topic_messages.append(message)

    def get_context(self):
        return {
            "topic": self.topic,
            "messages": self.messages,
            "repeat_count": self.repeat_count
        }

    def clear(self):
        self.current_topic = None
        self.topic_messages = []
        self.repeat_count = 0


class ConversationManager:
    def __init__(self):
        self.conversations = {}
        self.contexts = {}
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
        if user_name in self.contexts:
            del self.contexts[user_name]

    def increment_failed_attempts(self, user_name):
        self.failed_attempts[user_name] = self.failed_attempts.get(user_name, 0) + 1

    def get_failed_attempts(self, user_name):
        return self.failed_attempts.get(user_name, 0)

    def reset_failed_attempts(self, user_name):
        self.failed_attempts[user_name] = 0

    def set_context(self, user_name, topic):
        if user_name not in self.contexts:
            self.contexts[user_name] = ConversationContext(topic)
        elif self.contexts[user_name].topic != topic:
            self.contexts[user_name] = ConversationContext(topic)
        else:
            self.contexts[user_name].repeat_count += 1

    def get_context(self, user_name):
        if user_name not in self.contexts:
            return {'topic': None, 'messages': [], 'repeat_count': 0}
        context = self.contexts[user_name]
        return {'topic': context.topic, 'messages': context.messages, 'repeat_count': context.repeat_count}

    def add_context_message(self, user_name, message):
        if user_name in self.contexts:
            self.contexts[user_name].messages.append(message)

    def clear_context_messages(self, user_name):
        if user_name in self.contexts:
            self.contexts[user_name].messages = []

    def get_context_repeat_count(self, user_name):
        return self.contexts.get(user_name, ConversationContext(None)).repeat_count

    def reset_context_repeat_count(self, user_name):
        if user_name in self.contexts:
            self.contexts[user_name].repeat_count = 0

    def clear_context(self, user_name):
        if user_name in self.contexts:
            del self.contexts[user_name]