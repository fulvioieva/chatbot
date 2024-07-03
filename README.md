# chatbot
chatbot

# Compilazione
docker-compose down
docker-compose up --build

# Istruzioni
Gli operatori possono controllare la lista dei follow-up necessari facendo una richiesta GET a /followup-list.
Dopo aver contattato un utente, l'operatore può rimuoverlo dalla lista facendo una richiesta POST a /remove-from-followup con il nome dell'utente.