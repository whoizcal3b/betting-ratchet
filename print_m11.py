import json

with open("ws_messages.json", "r", encoding="utf-8") as f:
    messages = json.load(f)

m11 = messages[11]
print(json.dumps(m11, indent=2))
