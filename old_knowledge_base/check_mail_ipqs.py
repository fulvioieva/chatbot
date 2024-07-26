# THIS SHOULD NEVER BE USED IN PRODUCTION AS IS!

# You may need to install Requests pip
# python -m pip install requests

import requests

input = input("enter a email to look up ")
key = "ejnA0aVotQsjDYMO7IDb6QijmoVH0yH2"
type = "email"
url = "https://www.ipqualityscore.com/api/json/leaked/%s/%s/%s" % (type,key,input)

x = requests.get(url).json()
if x["exposed"] == True:
    print("email was detected in leaked data")
else:
    print("email is not leaked")