text = 'This is a "test" of the quote. Here is another "quote" to see.'
import re
print(re.sub(r'["""].*?["""]', '', text))

text2 = 'A "missing quote deletes everything. More text here.'
print(re.sub(r'["""].*?["""]', '', text2))
