from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
betslip_comp = soup.find(lambda tag: "betslip" in tag.name.lower() or ("class" in tag.attrs and any("betslip" in c.lower() for c in tag["class"])))
if betslip_comp:
    print(f"Betslip component tag: <{betslip_comp.name} class='{betslip_comp.get('class', [])}'>")
    print(betslip_comp.prettify()[:2000])
else:
    print("No betslip component tag found directly.")
