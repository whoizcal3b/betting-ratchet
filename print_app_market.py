from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
panels = soup.find_all("div", class_=lambda c: c and "market" in c and "open" in c)
p0 = panels[0]
app_market = p0.find("app-market")
print("app-market in panel 0:")
print(app_market.prettify()[:2500])
