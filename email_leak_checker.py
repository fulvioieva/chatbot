# email_leak_checker.py
import http.client
import json

def check_email_leak(email):
    conn = http.client.HTTPSConnection("email-data-leak-checker.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': "a710adc5dbmsh15bcc1f973783dcp12c245jsn047de608caa4",
        'x-rapidapi-host': "email-data-leak-checker.p.rapidapi.com",
        'Content-Type': "application/json",
        'User-Agent': "Sophos-Chatbot"
    }
    
    conn.request("GET", f"/emaild?email={email}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    
    return json.loads(data.decode("utf-8"))
