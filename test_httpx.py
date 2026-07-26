import httpx
try:
    with httpx.Client(http2=True, verify=False) as client:
        res = client.get('https://jurnal.bsi.ac.id/', timeout=10)
        print("HTTPX GET STATUS:", res.status_code)
except Exception as e:
    print("HTTPX Error:", e)
