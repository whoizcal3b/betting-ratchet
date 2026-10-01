import json
import re

with open("ws_messages.json", "r", encoding="utf-8") as f:
    messages = json.load(f)

print(f"Total WS messages logged: {len(messages)}")

found_events = 0
for i, m in enumerate(messages):
    data_str = json.dumps(m)
    # Check for keywords related to speedway or results
    if any(k in data_str.lower() for k in ["speedway", "bristol", "finish", "winner", "result", "rank", "payout"]):
        found_events += 1
        d = m.get("data", {})
        typ = d.get("type", "")
        # print first few
        if found_events <= 10:
            print(f"\nMessage {i} ({m.get('dir')} - {typ}):")
            print(data_str[:400] + "...")

print(f"\nTotal matching result/speedway WS messages: {found_events}")
