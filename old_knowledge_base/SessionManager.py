from threading import Lock
from collections import defaultdict
import time

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.conversation_history = []
        self.last_interaction = time.time()
        self.failed_attempts = 0

    def add_message(self, message, is_user=True):
        self.conversation_history.append({"content": message, "is_user": is_user})
        self.last_interaction = time.time()

    def get_context(self):
        return "\n".join([f"{'User' if msg['is_user'] else 'Assistant'}: {msg['content']}" 
                          for msg in self.conversation_history[-5:]])  # ultimi 5 messaggi

    def increment_failed_attempts(self):
        self.failed_attempts += 1

    def reset_failed_attempts(self):
        self.failed_attempts = 0

class SessionManager:
    def __init__(self, session_timeout=1800):  # 30 minuti di timeout di default
        self.sessions = defaultdict(UserSession)
        self.session_timeout = session_timeout
        self.lock = Lock()

    def get_session(self, user_id):
        with self.lock:
            session = self.sessions[user_id]
            if time.time() - session.last_interaction > self.session_timeout:
                # Se la sessione è scaduta, creane una nuova
                session = self.sessions[user_id] = UserSession(user_id)
            return session

    def add_message(self, user_id, message, is_user=True):
        session = self.get_session(user_id)
        session.add_message(message, is_user)

    def get_context(self, user_id):
        return self.get_session(user_id).get_context()

    def increment_failed_attempts(self, user_id):
        self.get_session(user_id).increment_failed_attempts()

    def reset_failed_attempts(self, user_id):
        self.get_session(user_id).reset_failed_attempts()

    def get_failed_attempts(self, user_id):
        return self.get_session(user_id).failed_attempts

    def clear_conversation(self, user_id):
        with self.lock:
            if user_id in self.sessions:
                del self.sessions[user_id]