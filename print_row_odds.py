import re
from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
p0 = soup.find("div", class_=lambda c: c and "market" in c and "open" in c)
row0 = p0.find("div", class_=lambda c: c and "market-table-row" in c)

print("Row 0 children and odds:")
for child in row0.children:
    if child.name:
        print(f"Child: <{child.name} class='{child.get('class', [])}'> Text: '{child.get_text(strip=True)}'")
        # If it has buttons or odds
        for odd_btn in child.find_all(["button", "a", "span", "app-odd"]):
            if "odd" in str(odd_btn.get("class", [])) or re.match(r"^\d+\.\d{2}$", odd_btn.get_text(strip=True)):
                print(f"    Sub-element: <{odd_btn.name} class='{odd_btn.get('class', [])}'> -> '{odd_btn.get_text(strip=True)}'")
