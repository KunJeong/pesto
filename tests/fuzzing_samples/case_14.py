class Box:

    def __init__(self, payload):
        self.payload = payload

    def label(self):
        return str(self.payload)
box = Box(2)
label0 = box.label()
items = [box.payload, box.payload]
item_size = len(items)
text = box.label()
text_size = len(text)
with box as ctx:
    pass
