import os, base64, json

b64 = os.getenv("GCP_KEY_BASE64")
data = json.loads(base64.b64decode(b64))
print(data['client_email'])
