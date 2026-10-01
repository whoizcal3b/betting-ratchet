from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
panels = soup.find_all("div", class_=lambda c: c and "market" in c and "open" in c)
p0 = panels[0]

print("Panel 0 HTML snippet (first 2500 chars):")
print(p0.prettify()[:2500])
