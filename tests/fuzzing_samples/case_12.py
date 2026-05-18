raw = b'xyz'
invalid_raw = b'\xff'
blob = bytearray(raw)
pieces = [b for b in raw]
text = 'a'
byte_count = len(blob)
text2 = raw.decode('latin1')
text2_size = len(text2)
if raw:
    tail = raw[1:]
else:
    tail = b''
joined = raw + raw
joined_size = len(joined)
try:
    text.encode('nope')
finally:
    marker = 1
