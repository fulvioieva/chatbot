# ip_checker.py
import http.client
import json
import socket

def url_to_ip(url):
    # Rimuovi il protocollo se presente
    url = url.replace("http://", "").replace("https://", "")
    # Rimuovi il percorso se presente
    url = url.split('/')[0]
    try:
        return socket.gethostbyname(url)
    except socket.gaierror:
        return None

def check_ip(ip_address):
    conn = http.client.HTTPSConnection("netdetective.p.rapidapi.com")
    headers = {
        'x-rapidapi-key': "a710adc5dbmsh15bcc1f973783dcp12c245jsn047de608caa4",
        'x-rapidapi-host': "netdetective.p.rapidapi.com"
    }
    
    conn.request("GET", f"/query?ipaddress={ip_address}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    
    return json.loads(data.decode("utf-8"))