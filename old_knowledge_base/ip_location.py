import http.client

conn = http.client.HTTPSConnection("netdetective.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "a710adc5dbmsh15bcc1f973783dcp12c245jsn047de608caa4",
    'x-rapidapi-host': "netdetective.p.rapidapi.com"
}



conn.request("GET", "/query?ipaddress=8.8.8.8", headers=headers)
res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
