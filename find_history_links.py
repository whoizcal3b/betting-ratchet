from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
history_links = soup.find_all("a", href=lambda h: h and "history" in h)
for a in history_links:
    print(f"Text: '{a.get_text(strip=True)}' | title: '{a.get('title')}' | href: '{a.get('href')}'")
