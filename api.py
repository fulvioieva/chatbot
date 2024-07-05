import http.client

conn = http.client.HTTPSConnection("scampredictor.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "7d88a4fbb7msha3eeb887c021a8ep1224a4jsnffb093d6c687",
    'x-rapidapi-host': "scampredictor.p.rapidapi.com"
}

conn.request("GET", "/domain/syncroweb.com", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
