import requests as r

url = "https://consultaunificadapje.tse.jus.br/consulta-publica-unificada/processo/10/0"

headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6,es-AR;q=0.5,es-CL;q=0.4,es-CO;q=0.3,es-CR;q=0.2,es-HN;q=0.1,es-419;q=0.1,es-MX;q=0.1,es-PE;q=0.1,es-ES;q=0.1,es-US;q=0.1,es-UY;q=0.1,es-VE;q=0.1",
    "captcharesponse": "P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.3gAHp3Bhc3NrZXnFAXOqezKeg3A3EeWz_0kHNnc9tVY4q0bkn02kZnaWCkJA36a72aus5w5W3apanAgiMV6edOEuT60MJ221C5x8ac4PHQa_leeyPk3jGItLjQZmOFMEp1s1dEtwxJZodufWzxxV4whvKN0eGMjBrZCLnyFypn7fJPKxuOpaLJOm12By4jF-uu93Qos8rQ14-w2bXAoPaZ1_IUcOlsyKKzemCWGBvjsXYSXc_5UqEjHmyVg1ikZ4koX8JtB2t4BRqo5QTIapYs4XoPyECpEEIA4xRF6w8uDG7h5eYB_cz_AVKb9PSVX1sCjx0DSAv_ay77YpCzs0p5c2SnlsbR6Z9kwnEBFoFYRvSdjHZs94tYNVNDUxCVE1RUMJOscQjuJlJRPjYyNLdXU4fZwa2oN6E_iUyedC2tdJtmnVZc-K2ULNOeQcpuZUu6vYmY2ng4cLiNhlw5IS8ygsk_1TpF1proAxODK1n7I1wgjpql2vAi07ENjkIPtuNadzaXRla2V52SQxYTljMjRlMi00NjM0LTRhNDAtYjBjYS1lMGVlMjBhMGViZGOjZXhwzmipDP2icGQApWNkYXRh1AAApmNkYXRhMtQAAKJrcqgxZGFkYWJlYw.w06H2lpe_f1xp360U_2Ty8-7ydMyPalMeX4t-IcTCuU",
    "content-type": "application/json",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "cookie": "TSf273801c077=0887342584ab2800e3d39f8e08a6ce16500ad508737803c5bec44be776892fe27ea6ee2b401212b78437c135337332170887156efb172000caca96b38c80c8823f3dafab9901eda1bc895010724c2472b0800d06938f2281; TS00000000076=0887342584ab2800b8cd4afebaa792cdabf59ace445099db993fa618316d5540b828d8abd64bfd40f346fbdd0c4bdcc90835fd970109d000e6c9255093c811d6ca24e75cdad8804fa11964f72a1678f2f422873c2bb6aac5e55303b2afc25157d5f6bdf80bd5f11c26fc509167b4fac0b046c473c1de1b804ac3b89ec806c9abe7ea682ab2bbe6cfa4800205508ecdd9c95e4755996809f59acff036086d421f6e14b83d7c642a0d514875f3d4bef073d77c4e0897183030275ebd61d083d30d6ccfc38bd429c7c279b78febe5dd7d1720877c056ed6961dcb93385d2678b15aa0c743a74be4b24d8f604140aa7ef78d754934f5717c27304ad19d2a815b701fde66f5bc78dc9aa5; TSPD_101_DID=0887342584ab2800b8cd4afebaa792cdabf59ace445099db993fa618316d5540b828d8abd64bfd40f346fbdd0c4bdcc90835fd97010638007869a2158871459c443afc6eb3668f40d7358038964de4981885754fde0b16829f153f3e0b0d779b74ab1923aed0489b2a692a5ca5e3a7e8; sticky=4bb8e5ae31845b7edbb85432b926f4a5d5ef55be; TS01683a6d=0103a0ceaefb2280f722582a3766bfd4cb065c6ee960af3ed40a01953705a9afeda41a652996c03afb104cb769f35f699814d178d2d90e99ec27212257c9f33da392011d46; TSPD_101=0887342584ab2800b79c5857f7f872ab534702e64c1f31c0b1368d5bf4dcd925183c4a6633f0d086d27180721d62e0ef08e62d8df3051800e07e690a265045fcc32c77dcb8dae8e69b3ef36f7cb1ee81; TS4529b75d027=0887342584ab2000c67131dce8a0acabd688358c99a1569c007cce6c6feec042c147ff2a5335761308863687ae113000b5f92c7cb216dc3ca9b1afd3dd61b50e44bac8d8ca03b4a61b7f87ce35e40f8a494bd0b8c00ebf57be2ab82f036e97e8",
    "Referer": "https://consultaunificadapje.tse.jus.br/",
}

payload = {"partes.cpfCnpjParte": "24.754.612/0001-38", "filtrarPorNovoProcesso": True}


response = r.post(url, data=payload, headers=headers)

print(response.json())
