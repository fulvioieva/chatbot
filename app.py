# app.py

from flask import Flask, request, jsonify
import anthropic
import os
from knowledge_base import KnowledgeBase
from bot_behavior import BOT_INSTRUCTIONS
from followup_manager import FollowUpManager
from conversation_manager import ConversationManager
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
    
    # Aggiungi il messaggio dell'utente alla conversazione
    conversation_manager.add_message(user_name, user_message, is_user=True)
    
    # Recupera la conversazione completa
    conversation = conversation_manager.get_conversation(user_name)
    
    # Verifica se il messaggio riguarda problemi di malware, virus o spyware
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

    # Prepara il prompt con la conversazione completa
    conversation_history = "\n".join([f"{'Utente' if msg['is_user'] else 'Assistente'}: {msg['content']}" for msg in conversation])
    full_prompt = f"{BOT_INSTRUCTIONS}\n\n{context}\n\nStorico della conversazione:\n{conversation_history}\n\nRisposta:"

    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )

    bot_response = response.content[0].text

    # Aggiungi la risposta del bot alla conversazione
    conversation_manager.add_message(user_name, bot_response, is_user=False)

    # Verifica se il problema è stato risolto
    if "non è stato risolto" in bot_response.lower() or "contattare il supporto" in bot_response.lower():
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')