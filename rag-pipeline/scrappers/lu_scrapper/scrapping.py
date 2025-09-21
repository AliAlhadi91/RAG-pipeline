import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from utilities import settings
import sys
import os





def get_full_url(relative_url):
    return urljoin(settings.BASE_URL, relative_url)

def fetch_detail(link):
    """Fetch summary and document link from a ruling page"""
    try:
        res = requests.get(link, headers=settings.HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # PDF link
        pdf_tag = soup.find("a", id="MainContent_downloadPDF")
        full_doc = get_full_url(pdf_tag["href"]) if pdf_tag and pdf_tag.get("href") else None

        # Summary
        summary_tag = soup.find("div", id="MainContent_RulingText")
        summary = summary_tag.get_text(strip=True) if summary_tag else None

        return {"link_to_full_document": full_doc, "summary": summary}
    except Exception as e:
        print(f"⚠️ Detail fetch failed for {link}: {e}")
        return {"link_to_full_document": None, "summary": None}

def scrape_year(year):
    print(f"\n📘 Scraping year: {year}")
    results = []
    current_url = f"{settings.BASE_URL}/AdvancedRulingSearch.aspx?searchText=&AndOr=AND&typeid=0&courtID=0&depid=0&rulNumber=0&rulYear={year}&judjes=&desicionmonth=0&DesicionDay=0&DesicionYear=0&pageNumber=1&language=ar"

    while True:
        print(f"🔎 Fetching: {current_url}")
        res = requests.get(current_url, headers=settings.HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")

        container = soup.find("div", id="MainContent_mainLegTr")
        if not container:
            break

        blocks = container.find_all("div", class_="extra-wrap")
        if not blocks:
            break

        batch = []
        links_to_fetch = []

        for block in blocks:
            a_tag = block.find("a", href=True)
            h4 = a_tag.find("h4") if a_tag else None
            link = get_full_url(a_tag['href']) if a_tag else None
            title = h4.get_text(strip=True) if h4 else None
            list_items = block.find_all("li")
            tags = [li.get_text(strip=True) for li in list_items]

            entry = {
                "link": link,
                "title": title,
                "list": tags
            }

            if link:
                links_to_fetch.append((link, entry))
            else:
                entry["link_to_full_document"] = None
                entry["summary"] = None

            batch.append(entry)

        # Fetch details in parallel
        with ThreadPoolExecutor(max_workers=settings.MAX_THREADS) as executor:
            future_map = {executor.submit(fetch_detail, link): entry for link, entry in links_to_fetch}
            for future in as_completed(future_map):
                detail = future.result()
                target_entry = future_map[future]
                target_entry.update(detail)

        results.extend(batch)

        # Pagination check
        next_href = None
        for icon in soup.find_all("i", class_="fa fa-step-backward"):
            parent_a = icon.find_parent("a", href=True)
            parent_li = parent_a.find_parent("li") if parent_a else None
            if parent_a and parent_li:
                if "disabled" in parent_li.get("class", []):
                    next_href = None
                else:
                    next_href = parent_a['href']
                break

        if not next_href:
            break

        current_url = get_full_url(next_href)
        time.sleep(0.5)  # between page requests

    # Save results
    with open(f"rulings_{year}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(results)} rulings to rulings_{year}.json")


# ===== MAIN: Accept year from CLI =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, help="Year to scrape")
    args = parser.parse_args()

    try:
        scrape_year(args.year)
    except Exception as e:
        print(f"❗ Failed year {args.year}: {e}")
