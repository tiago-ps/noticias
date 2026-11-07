import json,os,re,html,datetime,urllib.request,xml.etree.ElementTree as ET
ROOT=os.path.dirname(os.path.dirname(__file__)); cfg=json.load(open(os.path.join(ROOT,'config/sources.json'),encoding='utf8')); out=[]
def clean(x): return re.sub(r'\\s+',' ',html.unescape(re.sub('<[^>]+>',' ',x or ''))).strip()
for s in cfg:
 try:
  req=urllib.request.Request(s['feed'],headers={'User-Agent':'RadarNoticias/1.0'})
  data=urllib.request.urlopen(req,timeout=20).read(); root=ET.fromstring(data)
  items=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
  for it in items[:30]:
   def val(tags):
    for t in tags:
     x=it.find(t)
     if x is not None and (x.text or '').strip(): return x.text.strip()
    return ''
   title=clean(val(['title','{http://www.w3.org/2005/Atom}title'])); link=val(['link','{http://www.w3.org/2005/Atom}link'])
   if not link:
    x=it.find('{http://www.w3.org/2005/Atom}link'); link=x.attrib.get('href','') if x is not None else ''
   desc=clean(val(['description','summary','{http://www.w3.org/2005/Atom}summary']))
   date=val(['pubDate','published','updated','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated']) or datetime.datetime.now(datetime.timezone.utc).isoformat()
   if title and link: out.append({'source':s['name'],'title':title,'summary':desc[:280],'url':link,'date':date})
 except Exception as e: print('Falha',s['name'],e)
seen=set(); unique=[]
for n in sorted(out,key=lambda x:x['date'],reverse=True):
 k=re.sub(r'\\W','',n['title'].lower())
 if k not in seen: seen.add(k); unique.append(n)
os.makedirs(os.path.join(ROOT,'data'),exist_ok=True)
json.dump(unique[:120],open(os.path.join(ROOT,'data/news.json'),'w',encoding='utf8'),ensure_ascii=False,indent=2)
open(os.path.join(ROOT,'data/.updated'),'w').write(datetime.datetime.now(datetime.timezone.utc).isoformat())
