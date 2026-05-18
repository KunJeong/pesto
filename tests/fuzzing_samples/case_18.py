num_text = '0'
bad_text = 'x'
hex_text = 'dead'
items = ['42', '12']
item_text = ':'.join(items)
if bad_text:
    probe = bad_text[0]
else:
    probe = ''
bits = list(hex_text)
bits_size = len(bits)
if bad_text:
    probe = bad_text[0]
else:
    probe = ''

def explode():
    return chr(-1)
explode()
