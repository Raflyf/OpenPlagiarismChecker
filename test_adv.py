from googlesearch import search
try:
    for res in search("Confusion Matrix 50 epoch", num_results=1, advanced=True):
        print(res.title)
        print(res.description)
        print(res.url)
except Exception as e:
    print(e)
