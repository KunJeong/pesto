grammar AbstractGrammar;

file
    : prog EOF
    ;

prog
    : length_hint_prog
    | subscript_prog
    | item_update_prog
    | binary_number_prog
    | inplace_number_prog
    | unary_number_prog
    | conversion_prog
    | sequence_prog
    | iter_prog
    | mapping_prog
    | classcheck_prog
    | format_buffer_prog
    | async_iter_prog
    | mixed_abstract_prog
    ;

length_hint_prog
    : length_hint_setup NL harmless_probe NL wrap_length_hint_error NL*
    ;

subscript_prog
    : subscript_setup NL harmless_probe NL wrap_subscript_error NL*
    ;

item_update_prog
    : item_update_setup NL harmless_probe NL item_update_error NL*
    ;

binary_number_prog
    : number_setup NL harmless_probe NL wrap_binary_error NL*
    ;

inplace_number_prog
    : number_setup NL harmless_probe NL inplace_error NL*
    ;

unary_number_prog
    : number_setup NL harmless_probe NL wrap_unary_error NL*
    ;

conversion_prog
    : conversion_setup NL harmless_probe NL wrap_conversion_error NL*
    ;

sequence_prog
    : sequence_setup NL harmless_probe NL wrap_sequence_error NL*
    ;

iter_prog
    : iter_setup NL harmless_probe NL iter_error NL*
    ;

mapping_prog
    : mapping_setup NL harmless_probe NL wrap_mapping_error NL*
    ;

classcheck_prog
    : classcheck_setup NL harmless_probe NL wrap_classcheck_error NL*
    ;

format_buffer_prog
    : format_buffer_setup NL harmless_probe NL wrap_format_buffer_error NL*
    ;

async_iter_prog
    : async_iter_setup NL harmless_probe NL wrap_async_iter_error NL*
    ;

mixed_abstract_prog
    : mixed_setup NL harmless_probe NL mixed_error NL*
    ;

length_hint_setup
    : 'import operator' NL
      'class BadLenHint:' NL
      '    def __iter__(self):' NL
      '        return self' NL
      '    def __next__(self):' NL
      '        raise StopIteration' NL
      '    def __length_hint__(self):' NL
      '        return "wide"' NL
      'class NegativeLenHint:' NL
      '    def __iter__(self):' NL
      '        return self' NL
      '    def __next__(self):' NL
      '        raise StopIteration' NL
      '    def __length_hint__(self):' NL
      '        return -1' NL
      'class ExplodingLen:' NL
      '    def __len__(self):' NL
      '        return "wide"' NL
      'bad_hint = BadLenHint()' NL
      'neg_hint = NegativeLenHint()' NL
      'bad_len = ExplodingLen()'
    ;

subscript_setup
    : 'class Plain:' NL
      '    pass' NL
      'class NoClassGetItem:' NL
      '    pass' NL
      'plain = Plain()' NL
      'items = [1, 2, 3]' NL
      'pair = (1, 2, 3)' NL
      'text = "abc"' NL
      'blob = b"abc"' NL
      'num = 7'
    ;

item_update_setup
    : 'class Plain:' NL
      '    pass' NL
      'plain = Plain()' NL
      'items = [1, 2, 3]' NL
      'pair = (1, 2, 3)' NL
      'text = "abc"' NL
      'blob = b"abc"' NL
      'mapping = {"a": 1}' NL
      'num = 3'
    ;

number_setup
    : 'class Plain:' NL
      '    pass' NL
      'plain = Plain()' NL
      'num = 7' NL
      'other = 3' NL
      'items = [1, 2]' NL
      'pair = (1, 2)' NL
      'text = "abc"' NL
      'blob = b"abc"' NL
      'mapping = {"a": 1}' NL
      'aset = {1, 2}'
    ;

conversion_setup
    : 'import operator' NL
      'class BadIndex:' NL
      '    def __index__(self):' NL
      '        return "zero"' NL
      'class BadInt:' NL
      '    def __int__(self):' NL
      '        return "zero"' NL
      'class BadTrunc:' NL
      '    def __trunc__(self):' NL
      '        return "zero"' NL
      'class BadFloat:' NL
      '    def __float__(self):' NL
      '        return "zero"' NL
      'class Plain:' NL
      '    pass' NL
      'bad_index = BadIndex()' NL
      'bad_int = BadInt()' NL
      'bad_trunc = BadTrunc()' NL
      'bad_float = BadFloat()' NL
      'plain = Plain()' NL
      'items = [1, 2, 3]'
    ;

sequence_setup
    : 'import operator' NL
      'class Plain:' NL
      '    pass' NL
      'plain = Plain()' NL
      'items = [1, 2, 3]' NL
      'pair = (1, 2, 3)' NL
      'text = "abc"' NL
      'mapping = {"a": 1}' NL
      'not_iter = 9'
    ;

iter_setup
    : 'import operator' NL
      'class Plain:' NL
      '    pass' NL
      'class BadIter:' NL
      '    def __iter__(self):' NL
      '        return 1' NL
      'plain = Plain()' NL
      'bad_iter = BadIter()' NL
      'not_iter = 9' NL
      'items = [1, 2, 3]'
    ;

mapping_setup
    : 'class BadKeys:' NL
      '    def keys(self):' NL
      '        return 1' NL
      '    def __getitem__(self, key):' NL
      '        return 2' NL
      'class BadItems:' NL
      '    def items(self):' NL
      '        return 1' NL
      'class BadValues:' NL
      '    def values(self):' NL
      '        return 1' NL
      'bad_keys = BadKeys()' NL
      'bad_items = BadItems()' NL
      'bad_values = BadValues()' NL
      'items = [1, 2, 3]' NL
      'plain_dict = {"a": 1}'
    ;

classcheck_setup
    : 'class Plain:' NL
      '    pass' NL
      'class PseudoClass:' NL
      '    __bases__ = 1' NL
      'plain = Plain()' NL
      'pseudo = PseudoClass()' NL
      'cls = Plain'
    ;

format_buffer_setup
    : 'import io' NL
      'class BadFormat:' NL
      '    def __format__(self, spec):' NL
      '        return 1' NL
      'class Plain:' NL
      '    pass' NL
      'bad_format = BadFormat()' NL
      'plain = Plain()' NL
      'reader = io.BytesIO(b"abc")' NL
      'readonly = b"abc"' NL
      'writable = bytearray(b"abc")'
    ;

async_iter_setup
    : 'class BadAIter:' NL
      '    def __aiter__(self):' NL
      '        return 1' NL
      'class Plain:' NL
      '    pass' NL
      'bad_aiter = BadAIter()' NL
      'plain = Plain()'
    ;

mixed_setup
    : 'import operator' NL
      'class Plain:' NL
      '    pass' NL
      'class BadIndex:' NL
      '    def __index__(self):' NL
      '        return "zero"' NL
      'class BadIter:' NL
      '    def __iter__(self):' NL
      '        return 1' NL
      'plain = Plain()' NL
      'bad_index = BadIndex()' NL
      'bad_iter = BadIter()' NL
      'items = [1, 2, 3]' NL
      'text = "abc"' NL
      'mapping = {"a": 1}' NL
      'num = 7'
    ;

harmless_probe
    : 'marker = 1'
    | 'marker = len([1, 2, 3])'
    | 'marker = str(type(object()).__name__)'
    | 'marker = sum([1, 2, 3])'
    | 'marker = list(range(2))'
    ;

wrap_length_hint_error
    : length_hint_error
    | 'tmp = ' length_hint_error
    | 'if True:' NL '    tmp = ' length_hint_error
    | 'thunk = lambda: ' length_hint_error NL 'thunk()'
    | 'def explode():' NL '    return ' length_hint_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' length_hint_error NL 'Runner().go()'
    ;

wrap_subscript_error
    : subscript_error
    | 'tmp = ' subscript_error
    | 'if True:' NL '    tmp = ' subscript_error
    | 'thunk = lambda: ' subscript_error NL 'thunk()'
    | 'def explode():' NL '    return ' subscript_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' subscript_error NL 'Runner().go()'
    ;

wrap_binary_error
    : binary_error
    | 'tmp = ' binary_error
    | 'if True:' NL '    tmp = ' binary_error
    | 'thunk = lambda: ' binary_error NL 'thunk()'
    | 'def explode():' NL '    return ' binary_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' binary_error NL 'Runner().go()'
    ;

wrap_unary_error
    : unary_error
    | 'tmp = ' unary_error
    | 'if True:' NL '    tmp = ' unary_error
    | 'thunk = lambda: ' unary_error NL 'thunk()'
    | 'def explode():' NL '    return ' unary_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' unary_error NL 'Runner().go()'
    ;

wrap_conversion_error
    : conversion_error
    | 'tmp = ' conversion_error
    | 'if True:' NL '    tmp = ' conversion_error
    | 'thunk = lambda: ' conversion_error NL 'thunk()'
    | 'def explode():' NL '    return ' conversion_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' conversion_error NL 'Runner().go()'
    ;

wrap_sequence_error
    : sequence_error
    | 'tmp = ' sequence_error
    | 'if True:' NL '    tmp = ' sequence_error
    | 'thunk = lambda: ' sequence_error NL 'thunk()'
    | 'def explode():' NL '    return ' sequence_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' sequence_error NL 'Runner().go()'
    ;

wrap_mapping_error
    : mapping_error
    | 'tmp = ' mapping_error
    | 'if True:' NL '    tmp = ' mapping_error
    | 'thunk = lambda: ' mapping_error NL 'thunk()'
    | 'def explode():' NL '    return ' mapping_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' mapping_error NL 'Runner().go()'
    ;

wrap_classcheck_error
    : classcheck_error
    | 'tmp = ' classcheck_error
    | 'if True:' NL '    tmp = ' classcheck_error
    | 'thunk = lambda: ' classcheck_error NL 'thunk()'
    | 'def explode():' NL '    return ' classcheck_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' classcheck_error NL 'Runner().go()'
    ;

wrap_format_buffer_error
    : format_buffer_error
    | 'tmp = ' format_buffer_error
    | 'if True:' NL '    tmp = ' format_buffer_error
    | 'thunk = lambda: ' format_buffer_error NL 'thunk()'
    | 'def explode():' NL '    return ' format_buffer_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' format_buffer_error NL 'Runner().go()'
    ;

wrap_async_iter_error
    : async_iter_error
    | 'tmp = ' async_iter_error
    | 'if True:' NL '    tmp = ' async_iter_error
    | 'thunk = lambda: ' async_iter_error NL 'thunk()'
    | 'def explode():' NL '    return ' async_iter_error NL 'explode()'
    | 'class Runner:' NL '    def go(self):' NL '        return ' async_iter_error NL 'Runner().go()'
    ;

length_hint_error
    : 'list(bad_hint)'
    | 'tuple(bad_hint)'
    | 'set(bad_hint)'
    | 'list(neg_hint)'
    | 'tuple(neg_hint)'
    | 'operator.length_hint(bad_hint)'
    | 'operator.length_hint(neg_hint)'
    | 'len(bad_len)'
    ;

subscript_error
    : 'plain[0]'
    | 'num[0]'
    | 'NoClassGetItem[int]'
    | 'items[None]'
    | 'items[{}]'
    | 'pair[None]'
    | 'text[[]]'
    | 'blob[{}]'
    | 'range(3)[1.5]'
    | 'memoryview(blob)[None]'
    ;

item_update_error
    : 'plain[0] = 1'
    | 'del plain[0]'
    | 'num[0] = 1'
    | 'del num[0]'
    | 'items[None] = 1'
    | 'del items[None]'
    | 'pair[0] = 1'
    | 'del pair[0]'
    | 'text[0] = "x"'
    | 'del text[0]'
    | 'blob[0] = 1'
    | 'del blob[0]'
    | 'plain[0:1] = [1]'
    | 'del plain[0:1]'
    ;

binary_error
    : 'plain + 1'
    | '1 + plain'
    | 'plain - 1'
    | 'num - items'
    | 'num & text'
    | 'num | mapping'
    | 'num ^ items'
    | 'num << text'
    | 'num >> mapping'
    | 'print >> text'
    | 'divmod(num, text)'
    | 'num @ other'
    | 'text @ text'
    | 'num // text'
    | 'num / items'
    | 'num % mapping'
    | 'pow(num, text)'
    | 'pow(num, other, text)'
    | 'text * text'
    | 'items * mapping'
    | 'blob * []'
    | 'aset + items'
    ;

inplace_error
    : 'value = Plain()' NL 'value += []'
    | 'value = Plain()' NL 'value -= 1'
    | 'value = 1' NL 'value |= text'
    | 'value = 1' NL 'value ^= items'
    | 'value = 1' NL 'value &= mapping'
    | 'value = 1' NL 'value <<= text'
    | 'value = 1' NL 'value >>= mapping'
    | 'value = 1' NL 'value @= text'
    | 'value = 1' NL 'value //= text'
    | 'value = 1' NL 'value /= items'
    | 'value = 1' NL 'value %= mapping'
    | 'value = [1]' NL 'value *= mapping'
    | 'value = "x"' NL 'value *= text'
    | 'value = 2' NL 'value **= text'
    ;

unary_error
    : '-items'
    | '+mapping'
    | '~text'
    | 'abs(plain)'
    | '-plain'
    | '+plain'
    | '~plain'
    ;

conversion_error
    : 'operator.index("x")'
    | 'operator.index(bad_index)'
    | 'range("x")'
    | 'items[bad_index]'
    | 'chr(bad_index)'
    | 'hex("x")'
    | 'oct(plain)'
    | 'bin([])'
    | 'int(plain)'
    | 'int(bad_int)'
    | 'int(bad_trunc)'
    | 'float(bad_float)'
    | 'float({})'
    | 'complex({})'
    | 'slice(0, 1).indices("x")'
    ;

sequence_error
    : 'len(plain)'
    | 'len(iter(items))'
    | 'operator.concat(plain, items)'
    | 'operator.concat(1, items)'
    | 'operator.getitem(plain, 0)'
    | 'operator.getitem(not_iter, 0)'
    | 'operator.setitem(plain, 0, 1)'
    | 'operator.delitem(plain, 0)'
    | 'operator.contains(not_iter, 1)'
    | 'operator.countOf(not_iter, 1)'
    | 'operator.indexOf(not_iter, 1)'
    | '1 in not_iter'
    | 'text * mapping'
    | 'items * text'
    | 'tuple(not_iter)'
    | 'list(not_iter)'
    ;

iter_error
    : 'iter(not_iter)'
    | 'iter(plain)'
    | 'iter(bad_iter)'
    | 'list(not_iter)'
    | 'tuple(not_iter)'
    | 'set(not_iter)'
    | 'dict(not_iter)'
    | 'operator.contains(not_iter, 1)'
    | 'operator.countOf(not_iter, 1)'
    | 'operator.indexOf(not_iter, 1)'
    | '1 in not_iter'
    | 'for x in not_iter:' NL '    marker = x'
    ;

mapping_error
    : 'dict(bad_keys)'
    | '{}.update(bad_keys)'
    | 'dict(bad_items)'
    | '{}.update(bad_items)'
    | 'bad_keys.keys()[0]'
    | 'bad_items.items()[0]'
    | 'bad_values.values()[0]'
    | 'plain_dict + items'
    | 'plain_dict[[]]'
    | 'len(iter(plain_dict))'
    ;

classcheck_error
    : 'isinstance(plain, 1)'
    | 'isinstance(plain, (Plain, 1))'
    | 'isinstance(plain, (int, (str, 1)))'
    | 'issubclass(plain, Plain)'
    | 'issubclass(Plain, 1)'
    | 'issubclass(Plain, (int, 1))'
    | 'issubclass(pseudo, Plain)'
    | 'issubclass(Plain, pseudo)'
    ;

format_buffer_error
    : 'format(bad_format, "")'
    | '"{}".format(bad_format)'
    | 'memoryview(plain)'
    | 'memoryview(1)'
    | 'reader.readinto(readonly)'
    | 'memoryview(writable)[:] = 1'
    | 'bytearray("abc")'
    | 'bytes(plain)'
    ;

async_iter_error
    : 'aiter(plain)'
    | 'aiter(1)'
    | 'aiter(bad_aiter)'
    ;

mixed_error
    : wrap_mixed_expr_error
    | mixed_stmt_error
    ;

wrap_mixed_expr_error
    : mixed_expr_error
    | 'tmp = ' mixed_expr_error
    | 'if True:' NL '    tmp = ' mixed_expr_error
    | 'thunk = lambda: ' mixed_expr_error NL 'thunk()'
    | 'def explode():' NL '    return ' mixed_expr_error NL 'explode()'
    ;

mixed_expr_error
    : 'plain[0]'
    | 'items[bad_index]'
    | 'num + mapping'
    | 'num << text'
    | 'text * mapping'
    | 'operator.index(bad_index)'
    | 'iter(bad_iter)'
    | 'operator.contains(num, 1)'
    | 'isinstance(plain, 1)'
    ;

mixed_stmt_error
    : 'plain[0] = 1'
    | 'del plain[0]'
    | 'value = 1' NL 'value |= text'
    | 'for x in num:' NL '    marker = x'
    ;

NL
    : '\n'
    ;

WS
    : [ \t\r]+ -> skip
    ;
