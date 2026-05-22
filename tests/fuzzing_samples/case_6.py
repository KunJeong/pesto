import re
text = 'ab12cd34'
parts = re.split('\\d+', text)
found = re.findall('[a-z]+', text)
found_count = len(found)
head = found[0]
head_size = len(head)
if re.search('ab', text):
    seen = True
else:
    seen = False
upper = text.upper()
upper_size = len(upper)
raise RuntimeError('boom')
