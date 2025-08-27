import requests as r

url = "https://consultaunificadapje.tse.jus.br/consulta-publica-unificada/processo/10/0"

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6,es-AR;q=0.5,es-CL;q=0.4,es-CO;q=0.3,es-CR;q=0.2,es-HN;q=0.1,es-419;q=0.1,es-MX;q=0.1,es-PE;q=0.1,es-ES;q=0.1,es-US;q=0.1,es-UY;q=0.1,es-VE;q=0.1",
    "captcharesponse": "",
    "content-type": "application/json",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "cookie": "",
    "Referer": "https://consultaunificadapje.tse.jus.br/",
}

payload = {"partes.cpfCnpjParte": "CNPJ", "filtrarPorNovoProcesso": True}


response = r.post(url, data=payload, headers=headers)

print(response.json())
