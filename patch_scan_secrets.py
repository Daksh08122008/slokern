with open("scripts/scan_secrets.py", "r") as f:
    content = f.read()

content = content.replace(
    "    re.compile(r'sk-fake-secret-1234567890'),\n",
    "    re.compile(r'sk-fake-secret-1234567890'),\n    re.compile(r'MIIEvAIBADANBgkqhkiG9w0BAQEFAASC'),\n"
)

with open("scripts/scan_secrets.py", "w") as f:
    f.write(content)
