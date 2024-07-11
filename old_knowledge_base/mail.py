import http.client

conn = http.client.HTTPSConnection("email-data-leak-checker.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "a710adc5dbmsh15bcc1f973783dcp12c245jsn047de608caa4",
    'x-rapidapi-host': "email-data-leak-checker.p.rapidapi.com",
    'Content-Type': "application/json",
    'User-Agent': "application-name"
}

conn.request("GET", "/emaild?email=fulvio.ieva@gmail.com", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
