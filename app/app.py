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
from conversation_manager import ConversationManager, ConversationContext
from email_leak_checker import check_email_leak
from ip_checker import check_ip, url_to_ip

ALLOWED_IP = '80.20.154.2'

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

logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"KNOWLEDGE_BASE_PATH: {KNOWLEDGE_BASE_PATH}")
logger.info(f"Files in KNOWLEDGE_BASE_PATH: {os.listdir(KNOWLEDGE_BASE_PATH)}")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['JSON_AS_ASCII'] = False
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

def handle_email_check(user_message):
    logger.info(f"Messaggio utente [{user_message}]")
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, user_message, re.IGNORECASE)
    
    if email_match:
        email = email_match.group(0)
        try:
            leak_result = check_email_leak(email)
            
            # Il risultato è già un dizionario, non c'è bisogno di decodificarlo
            if not isinstance(leak_result, dict):
                raise ValueError("Il risultato non è un dizionario come previsto")
            
            logger.info(f"Risultato grezzo del controllo email [{email}]: {json.dumps(leak_result, indent=2)}")
            
            formatted_result = format_leak_result(leak_result, email)
            return formatted_result
        except json.JSONDecodeError as e:
            logger.error(f"Errore di decodifica JSON per {email}: {str(e)}")
            return f"Si è verificato un errore nell'interpretazione del risultato per {email}. Per favore, riprova più tardi."
        except KeyError as e:
            logger.error(f"Chiave mancante nel risultato per {email}: {str(e)}")
            return f"Il formato del risultato per {email} non è quello atteso. Per favore, contatta il supporto tecnico."
        except ValueError as e:
            logger.error(f"Errore nel formato del risultato per {email}: {str(e)}")
            return f"Il formato del risultato per {email} non è valido. Per favore, contatta il supporto tecnico."
        except Exception as e:
            logger.error(f"Errore durante il controllo dell'email {email}: {str(e)}")
            return f"Si è verificato un errore durante il controllo dell'email {email}. Per favore, riprova più tardi."
    
    return "Non ho trovato un indirizzo email valido nel messaggio. Per favore, inserisci un indirizzo email da controllare."

def format_leak_result(result, email):
    if not result or 'status' not in result or result['status'] != 'ok':
        return f"Si è verificato un errore durante il controllo dell'email {email}. Per favore, riprova più tardi."

    if result['message'] == "No public dataleak on it":
        return f"Non sono state trovate fughe di dati pubbliche per l'email {email}.\n\n" \
               "Tuttavia, è sempre una buona pratica:\n" \
               "1. Utilizzare password uniche e complesse per ogni account.\n" \
               "2. Attivare l'autenticazione a due fattori (2FA) dove possibile.\n" \
               "3. Monitorare regolarmente l'attività dei tuoi account.\n" \
               "4. Essere cauti con le email di phishing e i tentativi di ingegneria sociale."

    if 'results' not in result or not result['results']:
        return f"Non sono state trovate informazioni specifiche per l'email {email}."

		
    leaks = result['results']
    unique_databases = set()
    compromised_passwords = set()
    hashed_passwords = set()
    other_info = set()

	
    response = f"Risultato del controllo per {email}:\n\n"
    response += f"Numero di fughe di dati rilevate: {len(leaks)}\n\n"

    for leak in leaks:
        if 'database_name' in leak and leak['database_name']:
            unique_databases.add(leak['database_name'])
        
        if 'password' in leak and leak['password']:
            compromised_passwords.add(leak['password'])
        
        if 'hashed_password' in leak and leak['hashed_password']:
            hashed_passwords.add(leak['hashed_password'])
        
        for key, value in leak.items():
            if value and key not in ['email', 'database_name', 'id', 'password', 'hashed_password']:
                other_info.add(f"{key}: {value}")

    response += f"Database compromessi: {', '.join(unique_databases)}\n\n"

    if compromised_passwords:
        response += "Password compromesse trovate (cambia immediatamente queste password):\n"
        for password in compromised_passwords:
            response += f"- {password}\n"
        response += "\n"

    if hashed_passwords:
        response += f"Sono state trovate {len(hashed_passwords)} password hashate. Anche se non sono in chiaro, si consiglia di cambiarle.\n\n"

    if other_info:
        response += "Altre informazioni potenzialmente compromesse:\n"
        for info in other_info:
            response += f"- {info}\n"
        response += "\n"

    response += "Azioni consigliate:\n"
    response += "1. Cambia immediatamente le password per tutti gli account associati a questa email, specialmente quelle elencate sopra.\n"
    response += "2. Se hai usato le stesse password su altri account, cambiale anche lì.\n"
    response += "3. Attiva l'autenticazione a due fattori (2FA) dove possibile.\n"
    response += "4. Monitora attentamente l'attività dei tuoi account per eventuali accessi non autorizzati.\n"
    response += "5. Sii cauto con le email di phishing o tentativi di ingegneria sociale.\n"
    response += "6. Considera l'uso di un gestore di password per generare e memorizzare password uniche e complesse per ogni account.\n"
	
    return response
	
def handle_malware_related(user_name):
    with open(os.path.join(KNOWLEDGE_BASE_PATH, 'interceptx_malware_guide.json'), 'r') as f:
        intercept_x_info = json.load(f)
    return f"Informazioni su Intercept X per la protezione da malware:\n{json.dumps(intercept_x_info, indent=2)}"

def handle_other_requests(user_message):
    relevant_info = kb.get_relevant_info(user_message)
    return f"Informazioni rilevanti dalla knowledge base:\n" + "\n".join(str(info) for info in relevant_info)

def handle_ip_or_url_check(user_message):
    url_match = re.search(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_message)
    if url_match:
        url = url_match.group(0)
        ip_address = url_to_ip(url)
        if ip_address:
            ip_info = check_ip(ip_address)
            return f"Informazioni sull'URL {url} (IP: {ip_address}):\n{json.dumps(ip_info, indent=2)}"
        else:
            return f"Non è stato possibile risolvere l'URL {url} in un indirizzo IP."
    
    ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', user_message)
    if ip_match:
        ip_address = ip_match.group(0)
        ip_info = check_ip(ip_address)
        logger.info(f"Risultato grezzo del controllo ip: {json.dumps(ip_info, indent=2)}")
        return f"Informazioni sull'indirizzo IP {ip_address}:\n{json.dumps(ip_info, indent=2)}"
    
    return "Non ho trovato un IP o URL valido nel messaggio. Puoi fornire un indirizzo IP o un URL da controllare?"

def get_bot_presentation():
    file_path = os.path.join(KNOWLEDGE_BASE_PATH, 'bot_presentation.txt')
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                presentation = f.read().strip()
            return presentation
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            return "Sono un assistente virtuale specializzato in sicurezza informatica. Sono qui per aiutarti con domande su malware, controlli di email e IP, e altre questioni di cybersecurity."
    
    # Se nessuna codifica funziona, usiamo una presentazione di fallback
    return "Sono un assistente virtuale specializzato in sicurezza informatica. Sono qui per aiutarti con domande su malware, controlli di email e IP, e altre questioni di cybersecurity."

def restrict_to_ip(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        if client_ip != ALLOWED_IP:
            logger.warning(f"Tentativo di accesso bloccato da IP non autorizzato: {client_ip}")
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function	

def determine_context(message):
    # Espressione regolare per identificare un indirizzo email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    if any(keyword in message.lower() for keyword in ['contattare assistenza', 'parlare con un operatore', 'supporto tecnico', 'assistenza umana', 'assistenza cyber', 'bisogno di assistenza']):
        return "assistenza"
    elif re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', message) or re.search(r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message):
        return "ip_url_check"
    elif any(keyword in message.lower() for keyword in ['malware', 'virus', 'spyware', 'malware?', 'virus?', 'spyware?']):
        return "malware"
    elif (any(keyword in message.lower() for keyword in ['mail', 'email', 'mail?', 'email?', 'posta', 'posta?']) and not any(keyword in message.lower() for keyword in ['ricevuto', 'mandato', 'sospetta'])) or re.search(email_pattern, message, re.IGNORECASE):
        return "email_check"
    else:
        return "general"
		
def convert_newlines_to_html(text):
    return text.replace('\n', '<br/>')
	
@app.route('/chat', methods=['POST'])
@error_handler
@restrict_to_ip
def chat():
    try:
        rate_limited_chat()
        
        user_message = request.json['message']
        user_name = request.json.get('user_name', 'Anonymous')
        
        conversation_manager.add_message(user_name, user_message, is_user=True)
        current_context = conversation_manager.get_context(user_name)
			
        # Gestisci la richiesta di presentazione
        if user_message.lower() in ["ciao, presentati in 2 righe!", "presentati", "chi sei?"]:
            bot_response = get_bot_presentation()
            conversation_manager.add_message(user_name, bot_response, is_user=False)
            logger.info(f"Utente {user_name}: Richiesta di presentazione del bot")
            return jsonify({"response": bot_response})

        new_context = determine_context(user_message)
        conversation_manager.set_context(user_name, new_context)

        context = conversation_manager.get_context(user_name)
        repeat_count = conversation_manager.get_context_repeat_count(user_name)

        logger.info(f"Utente {user_name}: Contesto - {new_context}, Ripetizioni: {repeat_count}")

        if repeat_count == 0:
            logger.info(f"Utente {user_name}: Contesto impostato - {new_context}")
        elif repeat_count >= 3:
            logger.info(f"Utente {user_name}: History della conversazione svuotata per ripetizione del contesto")
        else:
            logger.info(f"Utente {user_name}: Continuazione del contesto - {new_context}")	
				
        # Verifica se l'utente chiede di contattare l'assistenza
        if any(keyword in user_message.lower() for keyword in ['contattare assistenza', 'parlare con un operatore', 'supporto tecnico', 'assistenza umana', 'assistenza cyber', 'bisogno di assistenza']):
            bot_response = handle_assistance_request(user_name, user_message)
            conversation_manager.add_message(user_name, bot_response, is_user=False)
            logger.info(f"Utente {user_name}: Richiesta assistenza operatore")
            return jsonify({"response": bot_response})

        # Verifica se l'utente chiede di cambiare argomento
        if "cambia argomento" in user_message.lower() or "nuovo problema" in user_message.lower():
            conversation_manager.clear_context(user_name)
            current_context = None
            bot_response = "Ok, cambiamo argomento. Come posso aiutarti?"
            conversation_manager.add_message(user_name, bot_response, is_user=False)
            logger.info(f"Utente {user_name}: Cambio di argomento richiesto")
            return jsonify({"response": bot_response})

        # Determina il nuovo contesto basato sull'ultima domanda
        new_context = determine_context(user_message)

        # Cambia il contesto se è diverso dall'attuale o se non c'è un contesto corrente
        context_changed = False
        if not current_context or current_context.get('topic') != new_context:
            conversation_manager.set_context(user_name, new_context)
            logger.info(f"Utente {user_name}: Nuovo contesto impostato - {new_context}")
            context = new_context
            context_changed = True
        else:
            context = current_context.get('topic')
            logger.info(f"Utente {user_name}: Continuazione del contesto - {context}")

        # Se il contesto è cambiato, svuota la history della conversazione
        if context_changed:
            conversation_manager.clear_context_messages(user_name)
            logger.info(f"Utente {user_name}: History della conversazione svuotata per nuovo contesto")

        if context == "ip_url_check":
            bot_response = handle_ip_or_url_check(user_message)
        elif context == "email_check":
            bot_response = handle_email_check(user_message)
            # Se non è stato fornito un indirizzo email valido, non chiamare Claude
            if "Per favore, inserisci un indirizzo email da controllare." in bot_response:
                conversation_manager.add_message(user_name, bot_response, is_user=False)
                conversation_manager.add_context_message(user_name, bot_response)
                return jsonify({"response": bot_response})
        elif context == "malware":
            bot_response = handle_malware_related(user_name)
        else:
            bot_response = handle_other_requests(user_message)

        conversation_manager.add_context_message(user_name, bot_response)

        # Costruisci il prompt per Claude solo se non siamo nel caso email_check senza email valida
        if context != "email_check":
            conversation_manager.add_context_message(user_name, user_message)	
            context_messages = conversation_manager.get_context(user_name)['messages']
            conversation_history = "\n".join([f"{'Utente' if i % 2 == 0 else 'Assistente'}: {msg}" for i, msg in enumerate(context_messages)])
            full_prompt = f"{BOT_INSTRUCTIONS}\n\nContesto corrente: {context}\n\nStorico della conversazione:\n{conversation_history}\n\nAssistente: Fornisci solo la tua risposta, non simulare domande o risposte dell'utente."
            #logger.info(f"Messaggio bot [{full_prompt}]")

            #logger.info(f"INFORMAZIONI [{context_messages}]")
		
			# Ottieni la risposta da Claude
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
        else:
            logger.info(f"Salto la richiesta a Claude")
            bot_response = "\n".join([f"{msg}" for i, msg in enumerate(conversation_manager.get_context(user_name)['messages'])])
            logger.info(f"Utente {user_name}: {bot_response}")
            bot_response = convert_newlines_to_html(bot_response)
            conversation_manager.clear_context(user_name)

        # Verifica se il problema è stato risolto
        if any(phrase in user_message.lower() for phrase in ["non è stato risolto", "non ho risolto", "da un operatore"]):
            conversation_manager.increment_failed_attempts(user_name)
            failed_attempts = conversation_manager.get_failed_attempts(user_name)
            
            if failed_attempts >= 2:
                if user_name not in followup_manager.get_followup_list():
                    followup_manager.add_to_followup(user_name, user_message)
                    bot_response = "\n\nHo notato che stai avendo difficoltà a risolvere il problema. Ho aggiunto il tuo nominativo alla lista per assistenza da parte di un operatore."
                    conversation_manager.reset_failed_attempts(user_name)
                    conversation_manager.clear_context(user_name)
                    logger.info(f"Utente {user_name}: Richiesta assistenza umana dopo ripetuti tentativi falliti")
                else:
                    logger.info(f"Utente {user_name}: Houston abbiamo un problema")
            else:
                bot_response = f"\n\nSe il problema persiste, prova a fornire più dettagli o a riformulare la tua domanda."
                logger.info(f"Utente {user_name}: Tentativo fallito numero {failed_attempts}")
        else:
            conversation_manager.reset_failed_attempts(user_name)
            logger.info(f"Utente {user_name}: Reset di conversation manager")
        # Rimuovi eventuali parti della risposta che simulano l'input dell'utente
        bot_response = re.sub(r'Utente:.*', '', bot_response, flags=re.DOTALL).strip()
        
        # Aggiungi la risposta del bot alla conversazione
        conversation_manager.add_message(user_name, bot_response, is_user=False)
        conversation_manager.add_context_message(user_name, bot_response)
        
        logger.info(f"Utente {user_name}: Risposta fornita nel contesto {context}")
            
        return jsonify({"response": convert_newlines_to_html(bot_response)})
    
    except Exception as e:
        logger.exception(f"Errore durante l'elaborazione della chat: {str(e)}")
        return jsonify({"error": "Si è verificato un errore durante l'elaborazione della richiesta."}), 500

@app.route('/followup-list', methods=['GET'])
@error_handler
@restrict_to_ip
def get_followup_list():
    return jsonify(followup_manager.get_followup_list())

@app.route('/remove-from-followup', methods=['POST'])
@error_handler
@restrict_to_ip
def remove_from_followup():
    user_name = request.json['user_name']
    followup_manager.remove_from_followup(user_name)
    conversation_manager.clear_conversation(user_name)
    return jsonify({"message": f"{user_name} rimosso dalla lista di follow-up e la conversazione è stata cancellata"})


@app.route('/update_knowledge', methods=['POST'])
@restrict_to_ip
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
@restrict_to_ip
def submit_feedback():
    user_name = request.json['user_name']
    feedback = request.json['feedback']
    rating = request.json['rating']
    # Salva il feedback in un database o file
    save_feedback(user_name, feedback, rating)
    return jsonify({"message": "Grazie per il tuo feedback!"})		
		
@app.route('/threat-report', methods=['GET'])
@restrict_to_ip
def generate_threat_report():
    # Logica per generare un report sulle minacce rilevate
    report = generate_report()
    return jsonify(report)

@app.route('/admin-notify', methods=['POST'])
@restrict_to_ip
def notify_admin():
    message = request.json['message']
    send_admin_notification(message)
    return jsonify({"message": "Notifica inviata all'amministratore"})
	
@app.route('/check-updates', methods=['GET'])
@restrict_to_ip
def check_for_updates():
    # Logica per verificare gli aggiornamenti disponibili
    updates = check_sophos_updates()
    return jsonify(updates)	
	
@app.route('/debug/failed-attempts', methods=['GET'])
@error_handler
@restrict_to_ip
def debug_failed_attempts():
    return jsonify(conversation_manager.failed_attempts)
	
if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0')