import re
from bs4 import BeautifulSoup

with open("page_dom.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find all open market panels
panels = soup.find_all("div", class_=lambda c: c and "market" in c and "open" in c)
print(f"Total open race panels found: {len(panels)}")

for idx, panel in enumerate(panels):
    # Race title & ID
    header = panel.find(string=re.compile(r"Speedway Racing", re.I))
    header_text = header.strip() if header else "Unknown"

    # Race time / countdown
    time_badge = panel.find(class_=lambda c: c and ("time" in c or "clock" in c or "countdown" in c or "badge" in c))
    time_text = time_badge.get_text(strip=True) if time_badge else ""

    print(f"\n================ Race {idx+1} ================")
    print(f"Header: {header_text}")
    print(f"Time/Status: {time_text}")

    # Find participants
    participants = panel.find_all(class_=lambda c: c and "participant" in c)
    # Filter to actual runner rows
    runner_rows = [p for p in participants if p.find(class_=lambda c: c and "place-odd" in c)]
    print(f"Found {len(runner_rows)} runners with Place odds:")

    for r_idx, row in enumerate(runner_rows):
        # Runner number / badge
        num_el = row.find(class_=lambda c: c and ("number" in c or "num" in c or "badge" in c or "trap" in c or "jacket" in c))
        num_str = num_el.get_text(strip=True) if num_el else str(r_idx + 1)

        # Runner name
        name_el = row.find(class_=lambda c: c and ("name" in c or "title" in c))
        name_str = name_el.get_text(strip=True) if name_el else "Unknown"

        # Win odd
        win_el = row.find(class_=lambda c: c and "win-odd" in c)
        win_odd = win_el.get_text(strip=True) if win_el else "N/A"

        # Place odd
        place_el = row.find(class_=lambda c: c and "place-odd" in c)
        place_odd = place_el.get_text(strip=True) if place_el else "N/A"

        print(f"  Runner #{num_str}: {name_str:<20} | WIN: {win_odd:<5} | PLACE: {place_odd:<5}")

