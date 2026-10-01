import re
from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print(f"Total HTML length: {len(html)} characters")

# Find races
print("\n--- Searching for Race Containers ---")
# Look for text like "Speedway Racing: Bristol"
race_headers = soup.find_all(string=re.compile(r"Speedway Racing:\s*Bristol", re.I))
for rh in race_headers[:5]:
    parent = rh.parent
    # Go up a few levels to find the card container
    card = parent
    for _ in range(4):
        if card and card.parent:
            card = card.parent
    print(f"Header: {rh.strip()}")
    if card:
        print(f"Card tag: <{card.name} class='{card.get('class', [])}'>")

# Find odds buttons
print("\n--- Searching for Odds Elements ---")
# Odds text like 2.80, 1.48, etc.
odds_elements = soup.find_all(string=re.compile(r"^\s*\d+\.\d{2}\s*$"))
print(f"Found {len(odds_elements)} elements with decimal odds pattern")
for o in odds_elements[:8]:
    p = o.parent
    print(f"Odd: '{o.strip()}' -> <{p.name} class='{p.get('class', [])}' data-testid='{p.get('data-testid', '')}'> parent: <{p.parent.name} class='{p.parent.get('class', [])}'>")

# Find Betslip elements
print("\n--- Searching for Betslip Elements ---")
betslip = soup.find(class_=re.compile(r"betslip", re.I)) or soup.find(id=re.compile(r"betslip", re.I))
if betslip:
    print(f"Found Betslip container: <{betslip.name} class='{betslip.get('class', [])}'>")
else:
    print("No explicit .betslip container found by class, checking text...")
    for txt in ["Betslip", "Place bet", "Stake", "Login to place bets"]:
        matches = soup.find_all(string=re.compile(txt, re.I))
        for m in matches[:3]:
            print(f"Text '{txt}': parent <{m.parent.name} class='{m.parent.get('class', [])}'>")

