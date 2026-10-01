from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
panels = soup.find_all("div", class_=lambda c: c and "market" in c and "open" in c)
p0 = panels[0]

print("Children tags of panel 0:")
for child in p0.children:
    if child.name:
        print(f"<{child.name} class='{child.get('class', [])}'>")

print("\nAll elements with place-odd:")
place_odds = soup.find_all(class_=lambda c: c and "place-odd" in c)
print(f"Total place-odd elements: {len(place_odds)}")
for p in place_odds[:4]:
    print(f"Place odd text: '{p.get_text(strip=True)}'")
    parent = p.parent
    for _ in range(5):
        if parent:
            print(f"  Parent: <{parent.name} class='{parent.get('class', [])}'>")
            parent = parent.parent
