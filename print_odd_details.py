from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
p0 = soup.find("div", class_=lambda c: c and "market" in c and "open" in c)
row0 = p0.find("div", class_=lambda c: c and "market-table-row" in c)
app_odds = row0.find_all("app-odd")

for i, odd in enumerate(app_odds):
    print(f"app-odd {i} (Text: '{odd.get_text(strip=True)}'):")
    print(odd.prettify())
