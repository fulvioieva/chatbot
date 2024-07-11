# app.py

from flask import Flask, request, jsonify
import anthropic
import os
import re
import json
import logging

from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from ratelimit import limits, sleep_and_retry

from knowledge_base import KnowledgeBase
from bot_behavior import BOT_INSTRUCTIONS
from followup_manager import FollowUpManager
from conversation_manager import ConversationManager
from email_leak_checker import check_email_leak
from ip_checker import check_ip

# Configurazione
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
KNOWLEDGE_BASE_PATH = os.getenv('KNOWLEDGE_BASE_PATH', '/app/external_knowledge')
MAX_REQUESTS = int(os.getenv('MAX_REQUESTS', 100))
REQUEST_WINDOW = int(os.getenv('REQUEST_WINDOW', 60))

# Configurazione del logging
logging.basicConfig(level=logging.INFO if DEBUG else logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
kb = KnowledgeBase(KNOWLEDGE_BASE_PATH)
followup_manager = FollowUpManager()
conversation_manager = ConversationManager()

# Decoratore per il rate limiting
@sleep_and_retry
@limits(calls=MAX_REQUESTS, period=REQUEST_WINDOW)
def rate_limited_chat():
    pass

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Un errore è avvenuto durante l'esecuzione di {func.__name__}: {str(e)}")
            return jsonify({"error": "Si è verificato un errore interno. Riprova più tardi."}), 500
    return wrapper

def handle_assistance_request(user_name, user_message):
    if user_name not in followup_manager.get_followup_list():
        followup_manager.add_to_followup(user_name, user_message)
        return "Ho registrato la tua richiesta di assistenza. Un operatore ti contatterà al più presto. Grazie per la tua pazienza."
    return "La tua richiesta di assistenza è già stata registrata. Un operatore ti contatterà al più presto. Grazie per la tua pazienza."

def handle_ip_check(user_message):
    ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', user_message)
    if ip_match:
        logger.info('IP check related')
        ip_address = ip_match.group(0)
        ip_info = check_ip(ip_address)
        return f"Informazioni sull'indirizzo IP {ip_address}:\n{json.dumps(ip_info, indent=2)}"
    return None

def handle_email_check(user_message):
    keywordsmail = ['mail', 'email', 'mail?', 'email?', 'posta', 'posta?']
    is_mail_related = any(keyword in user_message.lower() for keyword in keywordsmail)
    if is_mail_related:
        logger.info('Email related')
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user_message)
        if email_match:
            email = email_match.group(0)
            leak_result = check_email_leak(email)
            return f"Risultato del controllo email leak per {email}:\n{json.dumps(leak_result, indent=2)}"
        return "L'utente non ha fornito una mail valida. Chiedi di inserire una mail per poterla controllare."
    return None

def handle_malware_related(user_name):
    logger.info('Malware related')
    failed_attempts = conversation_manager.get_failed_attempts(user_name)
    with open(os.path.join(KNOWLEDGE_BASE_PATH, 'interceptx_malware_guide.json'), 'r') as f:
        intercept_x_info = json.load(f)
    return f"Informazioni su Intercept X:\n{json.dumps(intercept_x_info, indent=2)}"

def handle_other_requests(user_message):
    relevant_info = kb.get_relevant_info(user_message)
    return f"Informazioni rilevanti dalla knowledge base:\n" + "\n".join(str(info) for info in relevant_info)

@app.route('/chat', methods=['POST'])
@error_handler
def chat():
    rate_limited_chat()
    
    user_message = request.json['message']
    user_name = request.json.get('user_name', 'Anonymous')
    
    conversation_manager.add_message(user_name, user_message, is_user=True)
    conversation = conversation_manager.get_conversation(user_name)
    
    # Verifica se l'utente chiede di contattare l'assistenza tecnica
    assistance_keywords = ['contattare assistenza', 'parlare con un operatore', 'supporto tecnico', 'assistenza umana', 'assistenza cyber', 'bisogno di assistenza']
    if any(keyword in user_message.lower() for keyword in assistance_keywords):
        logger.info('Richiesta assistenza')
        bot_response = handle_assistance_request(user_name, user_message)
        conversation_manager.add_message(user_name, bot_response, is_user=False)
        return jsonify({"response": bot_response})

    context = handle_ip_check(user_message) or handle_email_check(user_message)
    
    if not context:
        keywords = ['malware', 'virus', 'spyware']
        is_malware_related = any(keyword in user_message.lower() for keyword in keywords)
        if is_malware_related:
            context = handle_malware_related(user_name)
        else:
            context = handle_other_requests(user_message)

    conversation_history = "\n".join([f"{'Utente' if msg['is_user'] else 'Assistente'}: {msg['content']}" for msg in conversation])
    full_prompt = f"{BOT_INSTRUCTIONS}\n\n{context}\n\nStorico della conversazione:\n{conversation_history}\n\nAssistente: Fornisci solo la tua risposta, non simulare domande o risposte dell'utente."

    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=500,
        temperature=0.1,
        top_k=10,
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )

    bot_response = response.content[0].text

    # Verifica se il problema è stato risolto
    if any(phrase in user_message.lower() for phrase in ["non è stato risolto", "non ho risolto", "da un operatore"]):
        conversation_manager.increment_failed_attempts(user_name)
        failed_attempts = conversation_manager.get_failed_attempts(user_name)
        
        if failed_attempts >= 2:
            if user_name not in followup_manager.get_followup_list():
                followup_manager.add_to_followup(user_name, user_message)
                bot_response += "\n\nHo notato che stai avendo difficoltà a risolvere il problema. Ho aggiunto il tuo nominativo alla lista per assistenza da parte di un operatore."
                conversation_manager.reset_failed_attempts(user_name)
        else:
            bot_response += f"\n\nSe il problema persiste, prova a fornire più dettagli o a riformulare la tua domanda. Questo è il tentativo numero {failed_attempts}."
    else:
        conversation_manager.reset_failed_attempts(user_name)
        
    # Rimuovi eventuali parti della risposta che simulano l'input dell'utente
    bot_response = re.sub(r'Utente:.*', '', bot_response, flags=re.DOTALL).strip()
    
    # Aggiungi la risposta del bot alla conversazione
    conversation_manager.add_message(user_name, bot_response, is_user=False)        
        
    return jsonify({"response": bot_response})

@app.route('/followup-list', methods=['GET'])
@error_handler
def get_followup_list():
    return jsonify(followup_manager.get_followup_list())

@app.route('/remove-from-followup', methods=['POST'])
@error_handler
def remove_from_followup():
    user_name = request.json['user_name']
    followup_manager.remove_from_followup(user_name)
    conversation_manager.clear_conversation(user_name)
    return jsonify({"message": f"{user_name} rimosso dalla lista di follow-up e la conversazione è stata cancellata"})

if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0')

@app.route('/followup-list', methods=['GET'])
def get_followup_list():
    return jsonify(followup_manager.get_followup_list())

@app.route('/remove-from-followup', methods=['POST'])
def remove_from_followup():
    user_name = request.json['user_name']
    followup_manager.remove_from_followup(user_name)
    conversation_manager.clear_conversation(user_name)
    return jsonify({"message": f"{user_name} rimosso dalla lista di follow-up e la conversazione è stata cancellata"})

@app.route('/update_knowledge', methods=['POST'])
def update_knowledge():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(kb.directory, filename))
        kb.last_update = datetime.min  # Force reload on next query
        return jsonify({"message": "File updated successfully"}), 200
		
@app.route('/feedback', methods=['POST'])
def submit_feedback():
    user_name = request.json['user_name']
    feedback = request.json['feedback']
    rating = request.json['rating']
    # Salva il feedback in un database o file
    save_feedback(user_name, feedback, rating)
    return jsonify({"message": "Grazie per il tuo feedback!"})		
		
@app.route('/threat-report', methods=['GET'])
def generate_threat_report():
    # Logica per generare un report sulle minacce rilevate
    report = generate_report()
    return jsonify(report)

@app.route('/admin-notify', methods=['POST'])
def notify_admin():
    message = request.json['message']
    send_admin_notification(message)
    return jsonify({"message": "Notifica inviata all'amministratore"})
	
@app.route('/check-updates', methods=['GET'])
def check_for_updates():
    # Logica per verificare gli aggiornamenti disponibili
    updates = check_sophos_updates()
    return jsonify(updates)	
	
if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0')