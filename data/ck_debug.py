import requests

data = requests.get("https://api.cardkingdom.com/api/v2/pricelist").json()["data"]

search = "riptide gearhulk"
matches = [c for c in data if search in c.get("name", "").lower()]

for m in matches:
    print(m)
