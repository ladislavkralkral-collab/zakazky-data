#!/usr/bin/env python3
"""
GitHub Actions scraper – Webtrh.cz RSS feeds
Výstup: data/webtrh.json
"""
import requests
import json
import re
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
import time

FEEDS = {
    "Webtrh – Vývoj & Programování": "https://webtrh.cz/poptavky/poptavky-vyvoje-a-programovani/feed/",
    "Webtrh – PHP":                  "https://webtrh.cz/poptavky/php/feed/",
    "Webtrh – JavaScript":           "https://webtrh.cz/poptavky/javascript/feed/",
    "Webtrh – WordPress":            "https://webtrh.cz/poptavky/wordpress/feed/",
    "Webtrh – Mobilní aplikace":     "https://webtrh.cz/poptavky/mobilni-aplikace/feed/",
    "Webtrh – Python":               "https://webtrh.cz/poptavky/python/feed/",
    "Webtrh – Databáze":             "https://webtrh.cz/poptavky/databaze/feed/",
    "Webtrh – API & Integrace":      "https://webtrh.cz/poptavky/api/feed/",
    "Freelance.cz – Programování":   "https://www.freelance.cz/rss/projekty/programovani/",
    "Freelance.cz – Weby":           "https://www.freelance.cz/rss/projekty/tvorba-webu/",
    "Freelance.cz – Mobilní":        "https://www.freelance.cz/rss/projekty/mobilni-aplikace/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "cs,en;q=0.9",
}

def extract_budget(text):
    m = re.search(r'(\d[\d\s]*\d)\s*[-–až]*\s*(\d[\d\s]*\d)?\s*Kč', text)
    if m:
        from_val = int(re.sub(r'\s', '', m.group(1)))
        to_val   = int(re.sub(r'\s', '', m.group(2))) if m.group(2) else from_val
        label    = f"{from_val:,} Kč".replace(",", " ")
        if to_val != from_val:
            label = f"{from_val:,} – {to_val:,} Kč".replace(",", " ")
        return {"label": label, "value": from_val}
    return {"label": "neuvedeno", "value": 0}

items = []
seen  = set()

for source, url in FEEDS.items():
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # Zkontroluj jestli vrátil XML nebo HTML (Cloudflare block)
        if resp.text.strip().startswith("<!DOCTYPE") or "<html" in resp.text[:100]:
            print(f"[BLOCK] {source} → Cloudflare HTML")
            continue

        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            continue

        count = 0
        for item in channel.findall("item"):
            link  = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()
            desc  = (item.findtext("description") or "").strip()
            desc  = re.sub(r'<[^>]+>', '', desc).strip()
            pub   = item.findtext("pubDate") or ""

            if not link or link in seen:
                continue
            seen.add(link)

            try:
                ts = int(datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z").timestamp())
            except Exception:
                ts = int(time.time())

            budget = extract_budget(desc)

            items.append({
                "source":       source,
                "title":        title,
                "link":         link,
                "desc":         desc[:250],
                "timestamp":    ts,
                "pubDate":      pub,
                "budget":       budget["label"],
                "budget_value": budget["value"],
            })
            count += 1
            if count >= 15:
                break

        print(f"[OK] {source} → {count} položek")
        time.sleep(0.3)

    except Exception as e:
        print(f"[ERR] {source}: {e}")

# Seřaď podle data
items.sort(key=lambda x: x["timestamp"], reverse=True)

output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "total":        len(items),
    "items":        items
}

with open("data/webtrh.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ Uloženo: {len(items)} zakázek → data/webtrh.json")
