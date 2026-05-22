import json
payload = '{"a": 1, "b": 2}'
obj = json.loads(payload)
keys = list(obj)
key_count = len(keys)
pairs = list(obj.items())
pair_count = len(pairs)
vals = list(obj.values())
val_count = len(vals)

class Runner:

    def go(self):
        return __import__('definitely_missing_module_xyz')
Runner().go()
