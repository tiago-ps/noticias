import datetime
import email.utils
import html
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG = os.path.join(ROOT, "config", "sources.json")
OUTPUT = os.path.join(ROOT, "data", "news.json")
UPDATED = os.path.join(ROOT, "data", ".updated")

with open(CONFIG, encoding="utf-8") as f:
    sources = json.load(f)


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def text_from(item, names):
    for name in names:
        node = item.find(name)
        if node is not None:
            value = "".join(node.itertext()).strip()
            if value:
                return value
    return ""


def parse_date(value):
    if not value:
        return datetime.datetime.now(datetime.timezone.utc)

    try:
        return email.utils.parsedate_to_datetime(value).astimezone(datetime.timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass

    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(value)
        return (dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    except (TypeError, ValueError):
        return datetime.datetime.now(datetime.timezone.utc)


def get_link(item):
    for node in item.findall("{http://www.w3.org/2005/Atom}link"):
        href = node.attrib.get("href", "")
        if href:
            return href

    for name in ("link", "guid"):
        node = item.find(name)
        if node is not None and node.text:
            value = node.text.strip()
            if value.startswith(("http://", "https://")):
                return value

    return ""


def collect_source(source):
    request = urllib.request.Request(
        source["feed"],
        headers={
            "User-Agent": "RadarNoticias/1.0 (+https://tiago-ps.github.io/noticias/)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()

    root = ET.fromstring(data)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    result = []
    for item in items[:30]:
        title = clean(text_from(item, [
            "title",
            "{http://www.w3.org/2005/Atom}title",
        ]))

        link = get_link(item)

        summary = clean(text_from(item, [
            "description",
            "{http://purl.org/rss/1.0/modules/content/}encoded",
            "summary",
            "{http://www.w3.org/2005/Atom}summary",
            "{http://www.w3.org/2005/Atom}content",
        ]))

        date_raw = text_from(item, [
            "pubDate",
            "published",
            "updated",
            "{http://www.w3.org/2005/Atom}published",
            "{http://www.w3.org/2005/Atom}updated",
        ])

        if title and link:
            published = parse_date(date_raw)
            result.append({
                "source": source["name"],
                "category": source.get("category", ""),
                "title": title,
                "summary": summary[:280],
                "url": link,
                "date": published.isoformat(),
            })

    return result


news = []
errors = []

for source in sources:
    try:
        items = collect_source(source)
        news.extend(items)
        print(f"OK {source['name']}: {len(items)} itens")
    except Exception as exc:
        errors.append({"source": source["name"], "error": str(exc)})
        print(f"FALHA {source['name']}: {exc}")

seen = set()
unique = []

for item in sorted(news, key=lambda x: x["date"], reverse=True):
    key = re.sub(r"\W+", "", item["title"].casefold())
    if key not in seen:
        seen.add(key)
        unique.append(item)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(unique[:120], f, ensure_ascii=False, indent=2)

with open(UPDATED, "w", encoding="utf-8") as f:
    f.write(datetime.datetime.now(datetime.timezone.utc).isoformat())

print(f"TOTAL: {len(unique[:120])} notícias")
print(f"FONTES COM FALHA: {len(errors)}")
