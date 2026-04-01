import httpx
import json

response = httpx.get('http://localhost:8000/api/news', timeout=90)
data = response.json()

articles = data['articles']
war = [a for a in articles if a['category'] == 'War']
geo = [a for a in articles if a['category'] == 'Geopolitics']
other = [a for a in articles if a['category'] not in ['War', 'Geopolitics']]

print(f"Status: {response.status_code}")
print(f"Total articles: {data['total']}")
print(f"  War: {len(war)}")
print(f"  Geopolitics: {len(geo)}")
print(f"  Other: {len(other)}")

print(f"\n=== WAR ARTICLES (top 3 by importance) ===")
war_sorted = sorted(war, key=lambda a: -a['importance'])
for i, article in enumerate(war_sorted[:3], 1):
    print(f"{i}. [{article['importance']}⚡] {article['title'][:75]}")
    print(f"   Source: {article['source']} | {article['published'][:10]}")

print(f"\n=== GEOPOLITICS ARTICLES (top 3 by importance) ===")
geo_sorted = sorted(geo, key=lambda a: -a['importance'])
for i, article in enumerate(geo_sorted[:3], 1):
    print(f"{i}. [{article['importance']}⚡] {article['title'][:75]}")
    print(f"   Source: {article['source']} | {article['published'][:10]}")

print(f"\n=== OTHER CATEGORIES (sample) ===")
for category in set(a['category'] for a in other):
    count = len([a for a in other if a['category'] == category])
    print(f"  {category}: {count}")
