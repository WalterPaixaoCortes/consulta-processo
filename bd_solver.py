import requests

API_KEY = "f0eb72285062bed1e6062553bf857d484b8cd831b64eeda4d7f339f8996adf74"

headers = {
    # Step 1: Get your API token here: https://brightdata.com/cp/setting/users
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

data = {
    # Step 2: Get your zone here: https://brightdata.com/cp/zones
    "zone": "web_unlocker1",
    # Step 3: Set your target URL
    "url": "https://consultaunificadapje.tse.jus.br/#/public/inicial/index",
    # Step 4: Run `python index.py` commend on terminal
    "format": "raw",
}

# Make request to Bright Data Web Unlocker API
url = "https://api.brightdata.com/request"

response = requests.post(url, json=data, headers=headers)
print(response.text)
