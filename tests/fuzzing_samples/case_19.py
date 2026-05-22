import json
payload = '{"a": 1, "b": 2}'
obj = json.loads(payload)
keys = list(obj)
key_count = len(keys)
if 'a' in obj:
    picked = obj['a']
else:
    picked = 0
clone = dict(obj)
clone_size = len(clone)
clone = dict(obj)
clone_size = len(clone)

def inner():
    return obj['missing']

def outer():
    return inner()
outer()
