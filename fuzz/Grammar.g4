grammar Grammar;

file
    : program EOF
    ;

program
    : math_prog
    | text_prog
    | collection_prog
    | object_prog
    | bytes_prog
    | convert_prog
    | regex_prog
    | json_prog
    | path_prog
    | deque_prog
    | mixed_prog
    ;

math_prog
    : math_setup NL math_step NL math_step (NL math_step)? NL math_bad_site NL*
    ;

text_prog
    : text_setup NL text_step NL text_step (NL text_step)? NL text_bad_site NL*
    ;

collection_prog
    : collection_setup NL collection_step NL collection_step (NL collection_step)? NL collection_bad_site NL*
    ;

object_prog
    : object_setup NL object_step NL object_step (NL object_step)? NL object_bad_site NL*
    ;

bytes_prog
    : bytes_setup NL bytes_step NL bytes_step (NL bytes_step)? NL bytes_bad_site NL*
    ;

convert_prog
    : convert_setup NL convert_step NL convert_step (NL convert_step)? NL convert_bad_site NL*
    ;

regex_prog
    : regex_setup NL regex_step NL regex_step (NL regex_step)? NL regex_bad_site NL*
    ;

json_prog
    : json_setup NL json_step NL json_step (NL json_step)? NL json_bad_site NL*
    ;

path_prog
    : path_setup NL path_step NL path_step (NL path_step)? NL path_bad_site NL*
    ;

deque_prog
    : deque_setup NL deque_step NL deque_step (NL deque_step)? NL deque_bad_site NL*
    ;

mixed_prog
    : mixed_setup NL mixed_step NL mixed_step (NL mixed_step)? NL mixed_bad_site NL*
    ;

math_setup
    : 'import math' NL
      'value = ' num_lit NL
      'other = ' num_lit NL
      'flag = ' bool_lit NL
      'nums = [' pos_num_lit ', ' pos_num_lit ', ' pos_num_lit ']' NL
      'roots = [math.sqrt(x) for x in nums]' NL
      'root_count = len(roots)'
    ;

text_setup
    : 'flag = ' bool_lit NL
      'text = ' str_lit NL
      'upper = text.upper()' NL
      'parts = [c for c in text]' NL
      'part_count = len(parts)'
    ;

collection_setup
    : 'value = ' num_lit NL
      'nums = [' num_lit ', ' num_lit ', ' num_lit ']' NL
      'copy = nums.copy()' NL
      'mapping = {' key_lit ': ' num_lit ', ' key_lit ': ' num_lit '}' NL
      'pair = (nums[0], nums[1])' NL
      'seen = {' pos_num_lit ', ' pos_num_lit '}' NL
      'item_count = len(copy)'
    ;

object_setup
    : 'class Box:' NL
      '    def __init__(self, payload):' NL
      '        self.payload = payload' NL
      '    def label(self):' NL
      '        return str(self.payload)' NL
      'box = Box(' num_lit ')' NL
      'label0 = box.label()'
    ;

bytes_setup
    : 'raw = ' bytes_lit NL
      'invalid_raw = b"\\xff"' NL
      'blob = bytearray(raw)' NL
      'pieces = [b for b in raw]' NL
      'text = ' str_lit NL
      'byte_count = len(blob)'
    ;

convert_setup
    : 'num_text = ' digit_text_lit NL
      'bad_text = ' bad_text_lit NL
      'hex_text = ' hex_text_lit NL
      'items = [' digit_text_lit ', ' digit_text_lit ']' NL
      'item_text = ":".join(items)'
    ;

regex_setup
    : 'import re' NL
      'text = "ab12cd34"' NL
      'parts = re.split(r"\\d+", text)' NL
      'found = re.findall(r"[a-z]+", text)' NL
      'found_count = len(found)'
    ;

json_setup
    : 'import json' NL
      'payload = "{\\"a\\": 1, \\"b\\": 2}"' NL
      'obj = json.loads(payload)' NL
      'keys = list(obj)' NL
      'key_count = len(keys)'
    ;

path_setup
    : 'from pathlib import Path' NL
      'p = Path("alpha/beta.txt")' NL
      'child = p.with_suffix(".log")' NL
      'parts = list(p.parts)' NL
      'path_text = str(child)'
    ;

deque_setup
    : 'from collections import deque' NL
      'dq = deque([' num_lit ', ' num_lit '])' NL
      'copied = deque(dq)' NL
      'front = dq[0]' NL
      'length = len(dq)'
    ;

mixed_setup
    : 'import math' NL
      'flag = ' bool_lit NL
      'value = ' num_lit NL
      'text = ' str_lit NL
      'nums = [' pos_num_lit ', ' pos_num_lit ', ' pos_num_lit ']' NL
      'mapping = {' key_lit ': ' num_lit ', ' key_lit ': ' num_lit '}' NL
      'parts = [c for c in text]' NL
      'class Box:' NL
      '    pass' NL
      'box = Box()' NL
      'def build(seq):' NL
      '    return list(seq)' NL
      'built = build(nums)' NL
      'roots = [math.sqrt(x) for x in nums]' NL
      'from_map = list(mapping.values())'
    ;

math_step
    : 'total = 0' NL
      'for x in nums:' NL
      '    total = total + x'
    | 'bigger = max(nums)' NL
      'nonneg = bigger >= 0'
    | 'if value < other:' NL
      '    chosen = value' NL
      'else:' NL
      '    chosen = other'
    | 'tail = nums[1:]' NL
      'tail_count = len(tail)'
    | 'square_map = {x: x * x for x in nums}' NL
      'square_count = len(square_map)'
    ;

text_step
    : 'joined = text + upper' NL
      'joined_count = len(joined)'
    | 'if text:' NL
      '    first = text[0]' NL
      'else:' NL
      '    first = ""'
    | 'rev = text[::-1]' NL
      'rev_count = len(rev)'
    | 'sizes = [len(p) for p in parts]' NL
      'size_count = len(sizes)'
    | 'mapping = {c: ord(c) for c in text}' NL
      'mapping_count = len(mapping)'
    ;

collection_step
    : 'head = copy[0]' NL
      'same_head = head == nums[0]'
    | 'keys = list(mapping)' NL
      'key_size = len(keys)'
    | 'if nums:' NL
      '    small = min(nums)' NL
      'else:' NL
      '    small = 0'
    | 'pairs = [(k, mapping[k]) for k in mapping]' NL
      'pair_size = len(pairs)'
    | 'triple = pair + (value,)' NL
      'triple_size = len(triple)'
    ;

object_step
    : 'label = box.label()' NL
      'label_size = len(label)'
    | 'box.extra = ' num_lit NL
      'mirror = box.extra'
    | 'if hasattr(box, "payload"):' NL
      '    current = box.payload' NL
      'else:' NL
      '    current = 0'
    | 'text = box.label()' NL
      'text_size = len(text)'
    | 'items = [box.payload, box.payload]' NL
      'item_size = len(items)'
    ;

bytes_step
    : 'text2 = raw.decode("latin1")' NL
      'text2_size = len(text2)'
    | 'first = blob[0]' NL
      'first_copy = first'
    | 'joined = raw + raw' NL
      'joined_size = len(joined)'
    | 'if raw:' NL
      '    tail = raw[1:]' NL
      'else:' NL
      '    tail = b""'
    | 'nums = [x for x in blob]' NL
      'nums_size = len(nums)'
    ;

convert_step
    : 'n = int(num_text)' NL
      'n2 = n + 1'
    | 'f = float(num_text)' NL
      'f2 = f + 1.0'
    | 'combo = ":".join(items)' NL
      'combo_size = len(combo)'
    | 'bits = list(hex_text)' NL
      'bits_size = len(bits)'
    | 'if bad_text:' NL
      '    probe = bad_text[0]' NL
      'else:' NL
      '    probe = ""'
    ;

regex_step
    : 'joined = "-".join(parts)' NL
      'joined_size = len(joined)'
    | 'head = found[0]' NL
      'head_size = len(head)'
    | 'pairs = list(enumerate(found))' NL
      'pair_size = len(pairs)'
    | 'if re.search(r"ab", text):' NL
      '    seen = True' NL
      'else:' NL
      '    seen = False'
    | 'upper = text.upper()' NL
      'upper_size = len(upper)'
    ;

json_step
    : 'vals = list(obj.values())' NL
      'val_count = len(vals)'
    | 'text = json.dumps(obj)' NL
      'text_size = len(text)'
    | 'pairs = list(obj.items())' NL
      'pair_count = len(pairs)'
    | 'if "a" in obj:' NL
      '    picked = obj["a"]' NL
      'else:' NL
      '    picked = 0'
    | 'clone = dict(obj)' NL
      'clone_size = len(clone)'
    ;

path_step
    : 'suffix = child.suffix' NL
      'suffix_size = len(suffix)'
    | 'name = p.name' NL
      'name_size = len(name)'
    | 'parent = p.parent' NL
      'parent_text = str(parent)'
    | 'joined = p.joinpath("gamma")' NL
      'joined_text = str(joined)'
    | 'part_count = len(parts)'
    ;

deque_step
    : 'dq.append(' num_lit ')' NL
      'after = len(dq)'
    | 'rot = deque(dq)' NL
      'rot.rotate(1)'
    | 'items = list(dq)' NL
      'item_count = len(items)'
    | 'if dq:' NL
      '    head = dq[0]' NL
      'else:' NL
      '    head = 0'
    | 'pair = tuple(dq)' NL
      'pair_size = len(pair)'
    ;

mixed_step
    : 'total = 0' NL
      'for x in nums:' NL
      '    total = total + x'
    | 'merged = text + str(value)' NL
      'merged_size = len(merged)'
    | 'again = build(parts)' NL
      'again_size = len(again)'
    | 'if flag:' NL
      '    probe = built[0]' NL
      'else:' NL
      '    probe = value'
    | 'root_count = len(roots)'
    ;

math_bad_site : wrap_math_expr ;
text_bad_site : wrap_text_expr ;
collection_bad_site : wrap_collection_expr | 'for x in 1:' NL '    pass' ;
object_bad_site : wrap_object_expr | 'with box as ctx:' NL '    pass' ;
bytes_bad_site : wrap_bytes_expr ;
convert_bad_site : wrap_convert_expr ;
regex_bad_site : wrap_regex_expr | 'raise RuntimeError("boom")' ;
json_bad_site : wrap_json_expr ;
path_bad_site : wrap_path_expr ;
deque_bad_site : wrap_deque_expr | 'raise NotImplementedError("todo")' ;
mixed_bad_site : wrap_mixed_expr | 'def boom():' NL '    x = x + 1' NL 'boom()' ;

wrap_math_expr : wrap_math_base ;
wrap_text_expr : wrap_text_base ;
wrap_collection_expr : wrap_collection_base ;
wrap_object_expr : wrap_object_base ;
wrap_bytes_expr : wrap_bytes_base ;
wrap_convert_expr : wrap_convert_base ;
wrap_regex_expr : wrap_regex_base ;
wrap_json_expr : wrap_json_base ;
wrap_path_expr : wrap_path_base ;
wrap_deque_expr : wrap_deque_base ;
wrap_mixed_expr : wrap_mixed_base ;

wrap_math_base
    : math_bad_expr
    | 'tmp = ' math_bad_expr
    | 'if True:' NL '    ' math_bad_expr
    | 'thunk = lambda: ' math_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' math_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' math_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' math_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' math_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_text_base
    : text_bad_expr
    | 'tmp = ' text_bad_expr
    | 'if True:' NL '    ' text_bad_expr
    | 'thunk = lambda: ' text_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' text_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' text_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' text_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' text_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_collection_base
    : collection_bad_expr
    | 'tmp = ' collection_bad_expr
    | 'if True:' NL '    ' collection_bad_expr
    | 'thunk = lambda: ' collection_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' collection_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' collection_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' collection_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' collection_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_object_base
    : object_bad_expr
    | 'tmp = ' object_bad_expr
    | 'if True:' NL '    ' object_bad_expr
    | 'thunk = lambda: ' object_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' object_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' object_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' object_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' object_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_bytes_base
    : bytes_bad_expr
    | 'tmp = ' bytes_bad_expr
    | 'if True:' NL '    ' bytes_bad_expr
    | 'thunk = lambda: ' bytes_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' bytes_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' bytes_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' bytes_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' bytes_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_convert_base
    : convert_bad_expr
    | 'tmp = ' convert_bad_expr
    | 'if True:' NL '    ' convert_bad_expr
    | 'thunk = lambda: ' convert_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' convert_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' convert_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' convert_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' convert_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_regex_base
    : regex_bad_expr
    | 'tmp = ' regex_bad_expr
    | 'if True:' NL '    ' regex_bad_expr
    | 'thunk = lambda: ' regex_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' regex_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' regex_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' regex_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' regex_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_json_base
    : json_bad_expr
    | 'tmp = ' json_bad_expr
    | 'if True:' NL '    ' json_bad_expr
    | 'thunk = lambda: ' json_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' json_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' json_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' json_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' json_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_path_base
    : path_bad_expr
    | 'tmp = ' path_bad_expr
    | 'if True:' NL '    ' path_bad_expr
    | 'thunk = lambda: ' path_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' path_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' path_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' path_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' path_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_deque_base
    : deque_bad_expr
    | 'tmp = ' deque_bad_expr
    | 'if True:' NL '    ' deque_bad_expr
    | 'thunk = lambda: ' deque_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' deque_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' deque_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' deque_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' deque_bad_expr NL 'finally:' NL '    marker = 1'
    ;

wrap_mixed_base
    : mixed_bad_expr
    | 'tmp = ' mixed_bad_expr
    | 'if True:' NL '    ' mixed_bad_expr
    | 'thunk = lambda: ' mixed_bad_expr NL 'thunk()'
    | 'def explode():' NL '    return ' mixed_bad_expr NL 'explode()'
    | 'def inner():' NL '    return ' mixed_bad_expr NL 'def outer():' NL '    return inner()' NL 'outer()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' mixed_bad_expr NL 'Runner().go()'
    | 'try:' NL '    ' mixed_bad_expr NL 'finally:' NL '    marker = 1'
    ;

math_bad_expr
    : 'nums + {}'
    | 'roots[None]'
    | 'math.sqrt("x")'
    | 'math.log(-1.0)'
    | 'value < 1j'
    | 'range("x")'
    | 'pow(1, 1, 0)'
    | '1 / 0'
    | 'divmod(1, 0)'
    | 'math.exp(1000)'
    ;

text_bad_expr
    : 'text + 1'
    | 'upper - {}'
    | 'text[None]'
    | 'parts + {}'
    | 'ord(1)'
    | 'chr(text)'
    | 'text.index("zzz")'
    | 'text.encode(1)'
    | 'text.encode("nope")'
    | '"\u20ac".encode("ascii")'
    ;

collection_bad_expr
    : 'copy + {}'
    | 'mapping[0.5]'
    | 'mapping["missing"]'
    | 'mapping.pop("missing")'
    | 'copy[99]'
    | 'copy[None]'
    | 'seen[0]'
    | 'seen.remove(99)'
    | 'copy.remove(99)'
    | 'pair + {}'
    | 'nums - {}'
    | 'sum(1)'
    | 'next(iter([]))'
    | 'next(iter(()))'
    ;

object_bad_expr
    : 'box + []'
    | 'box.missing'
    | 'next(box)'
    | 'len(box)'
    | 'box[0]'
    | 'box < 1j'
    | 'box.payload[0]'
    ;

bytes_bad_expr
    : 'raw + text'
    | 'raw[None]'
    | 'raw.decode(1)'
    | 'invalid_raw.decode("utf-8")'
    | 'blob + {}'
    | 'memoryview(1)'
    | 'text.encode(1)'
    | 'text.encode("nope")'
    | '"\u20ac".encode("ascii")'
    ;

convert_bad_expr
    : 'int(bad_text)'
    | 'float(bad_text)'
    | 'complex(bad_text)'
    | 'int(num_text, 1)'
    | 'int(hex_text, 10)'
    | 'bytes([999])'
    | 'bytearray("x")'
    | 'chr(-1)'
    | 'float(10 ** 1000)'
    | 'bytes.fromhex("zz")'
    | 'int("xyz")'
    | 'float("-")'
    | 'complex("xyz")'
    | 'next(iter([]))'
    | 'next(iter(()))'
    ;

regex_bad_expr
    : 're.match(1, text)'
    | 're.search(text, 1)'
    | 're.compile("(")'
    | 're.sub("(", "-", text)'
    | 're.findall(1, text)'
    | 're.compile("[")'
    | 'next(iter([]))'
    | 're.fullmatch(1, text)'
    | 're.sub("[", "-", text)'
    | 'next(iter(()))'
    ;

json_bad_expr
    : 'json.loads(1)'
    | 'json.loads("{")'
    | 'obj["missing"]'
    | 'obj.pop("missing")'
    | 'obj["ghost"]'
    | 'obj.pop("ghost")'
    | 'json.loads("[1,]")'
    | 'obj + []'
    | 'json.dumps(set())'
    | '__import__("definitely_missing_module_xyz")'
    | '__import__("still_missing_module_abc")'
    | 'next(iter([]))'
    | 'next(iter(()))'
    ;

path_bad_expr
    : 'parts[None]'
    | 'parts[99]'
    | 'p.relative_to("zzz")'
    | 'p.with_name("")'
    | 'child / 1'
    | 'p.read_text(encoding=1)'
    | 'p.read_text()'
    | 'Path(".").read_text()'
    | 'Path(".").mkdir()'
    | 'Path("missing-file-xyz.txt").read_text()'
    | '1 / 0'
    ;

deque_bad_expr
    : 'dq[None]'
    | 'dq[99]'
    | 'dq.remove(99)'
    | 'dq.rotate("x")'
    | 'dq + []'
    | 'next(dq)'
    | 'deque().popleft()'
    | 'dq.remove("missing")'
    | 'dq[99]'
    | 'deque().pop()'
    | 'next(iter([]))'
    | 'next(iter(()))'
    ;

mixed_bad_expr
    : 'built[None]'
    | 'mapping + text'
    | 'box + mapping'
    | 'iter(1)'
    | 'divmod(1, 0)'
    | 'complex(mapping)'
    | 'roots + text'
    | 'from_map[None]'
    | 'next(iter([]))'
    | 'next(iter(()))'
    | 'next(x for x in [])'
    ;

num_lit
    : '-3'
    | '-1'
    | '0'
    | '1'
    | '2'
    | '3'
    | '4'
    | '7'
    | '10'
    ;

pos_num_lit
    : '0'
    | '1'
    | '2'
    | '3'
    | '4'
    | '7'
    | '10'
    ;

bool_lit
    : 'True'
    | 'False'
    ;

str_lit
    : '"a"'
    | '"ab"'
    | '"abc"'
    | '"xy"'
    | '"hello"'
    ;

bytes_lit
    : 'b"a"'
    | 'b"ab"'
    | 'b"xyz"'
    | 'b"hello"'
    ;

digit_text_lit
    : '"0"'
    | '"1"'
    | '"12"'
    | '"42"'
    ;

bad_text_lit
    : '"x"'
    | '"xyz"'
    | '"-"'
    ;

hex_text_lit
    : '"ff"'
    | '"dead"'
    ;

key_lit
    : '"k"'
    | '"x"'
    | '"name"'
    | '"id"'
    ;

NL
    : '\n'
    ;

WS
    : [ \t\r]+ -> skip
    ;
