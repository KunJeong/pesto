raw = b'ab'
invalid_raw = b'\xff'
blob = bytearray(raw)
pieces = [b for b in raw]
text = 'abc'
byte_count = len(blob)
first = blob[0]
first_copy = first
joined = raw + raw
joined_size = len(joined)
if raw:
    tail = raw[1:]
else:
    tail = b''
if True:
    text.encode(1)
