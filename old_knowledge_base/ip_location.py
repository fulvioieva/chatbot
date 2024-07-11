import http.client

conn = http.client.HTTPSConnection("ip-to-location4.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "a710adc5dbmsh15bcc1f973783dcp12c245jsn047de608caa4",
    'x-rapidapi-host': "ip-to-location4.p.rapidapi.com"
}


conn.request("GET", "/iplocation?ip=82.165.54.77", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
