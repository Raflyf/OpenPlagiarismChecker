import urllib.request
import urllib.parse
import json
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

query = urllib.parse.quote_plus('"This project does not have the access to Custom Search JSON API."')
req = urllib.request.Request('https://html.duckduckgo.com/html/?q=' + query, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
    print("HTML length:", len(html))
    print(html[:500])
except Exception as e:
    print(e)
