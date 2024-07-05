# app.py

from flask import Flask, request, jsonify
import anthropic
import os
import re
from knowledge_base import KnowledgeBase
from bot_behavior import BOT_INSTRUCTIONS
from followup_manager import FollowUpManager
from conversation_manager import ConversationManager
from email_leak_checker import check_email_leak
import json

app = Flask(__name__)
client = anthropic.Client(api_key=os.environ.get('ANTHROPIC_API_KEY'))
kb = KnowledgeBase('/app/external_knowledge')
followup_manager = FollowUpManager()
conversation_manager = ConversationManager()

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    user_name = request.json.get('user_name', 'Anonymous')
    
    conversation_manager.add_message(user_name, user_message, is_user=True)
    conversation = conversation_manager.get_conversation(user_name)
    
    # Verifica se il messaggio riguarda problemi di email
    if ('email' in user_message.lower() or 'mail' in user_message.lower()) and ('problema' in user_message.lower() or 'controllo' in user_message.lower()):
        # Estrai l'indirizzo email dal messaggio dell'utente
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user_message)
        if email_match:
            email = email_match.group(0)
            leak_result = check_email_leak(email)
            context = f"Risultato del controllo email leak per {email}:\n{json.dumps(leak_result, indent=2)}"
        else:
            context = "Non è stato possibile identificare un indirizzo email nel messaggio. Per favore, fornisci un indirizzo email valido."
    else:
        # Usa la logica esistente per altri tipi di domande
        keywords = ['malware', 'virus', 'spyware']
        is_malware_related = any(keyword in user_message.lower() for keyword in keywords)

        if is_malware_related:
            with open('/app/external_knowledge/sophos_interceptx_malware_guide.json', 'r') as f:
                intercept_x_info = json.load(f)
            context = "Informazioni su Sophos Intercept X:\n"
            context += json.dumps(intercept_x_info, indent=2)
        else:
            relevant_info = kb.get_relevant_info(user_message)
            context = "Informazioni rilevanti dalla knowledge base:\n"
            context += "\n".join(str(info) for info in relevant_info)

    conversation_history = "\n".join([f"{'Utente' if msg['is_user'] else 'Assistente'}: {msg['content']}" for msg in conversation])
    full_prompt = f"{BOT_INSTRUCTIONS}\n\n{context}\n\nStorico della conversazione:\n{conversation_history}\n\nAssistente: Fornisci solo la tua risposta, non simulare domande o risposte dell'utente."

    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
		temperature=0.1,
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )

    bot_response = response.content[0].text
	
	# Rimuovi eventuali parti della risposta che simulano l'input dell'utente
    bot_response = re.sub(r'Utente:.*', '', bot_response, flags=re.DOTALL)
    bot_response = bot_response.strip()
	
    # Aggiungi la risposta del bot alla conversazione
    conversation_manager.add_message(user_name, bot_response, is_user=False)

    # Verifica se il problema è stato risolto
    if "non è stato risolto" in user_message.lower() or "non ho risolto" in user_message.lower() or "secure2.sophos.com/it-it/support/contact-support.aspx" in bot_response.lower() or "www.sophos.com/support" in bot_response.lower():
        if user_name not in followup_manager.get_followup_list():
            followup_manager.add_to_followup(user_name, user_message)
            bot_response += "\n\nHo aggiunto il tuo nominativo alla lista per un follow-up da parte di un operatore."

    return jsonify({"response": bot_response})

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
    app.run(debug=True, host='0.0.0.0')