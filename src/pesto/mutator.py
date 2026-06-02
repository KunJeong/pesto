import re
from copy import deepcopy
from pathlib import Path

import pycparser
import pycparser.c_ast as c_ast
from pycparser import c_generator

from . import paths

CPYTHON_ROOT = paths.VENDOR_CPYTHON
CPYTHON_HEADERS = paths.CPYTHON_HEADERS

CPYTHON_DEFINES = [
    "-DPy_BUILD_CORE",
    "-DUSE_COMPUTED_GOTOS=0",
    "-DNDEBUG",
    "-D_Float32=float",
    "-D_Float64=double",
    "-D_Float128=long double",
    "-D_Float32x=double",
    "-D_Float64x=long double",
    "-D__float128=long double",
    "-D__signed__=signed",
    "-D__typeof__(...)=long",
    "-D__auto_type=int",
    "-D__int128=long long",
    "-Dassert(x)=((void)(x))",
    "-D_Atomic(tp)=tp",
    "-D_Static_assert(x,y)=",
    "-D_Thread_local=",
    "-D__builtin_offsetof(type,member)=((int)((char*)(&((type*)0)->member)-(char*)0))",
    "-U__inline",  "-D__inline=inline",
    "-U__inline__", "-D__inline__=inline",
]

CPYTHON_INCLUDE_PATHS = [
    str(CPYTHON_HEADERS),
    str(CPYTHON_ROOT),
    str(CPYTHON_ROOT / "Include"),
    str(CPYTHON_ROOT / "Include" / "cpython"),
    str(CPYTHON_ROOT / "Include" / "internal"),
]

DEFAULT_CPP_ARGS = [
    "-E",
    "-D__attribute__(x)=",
    "-D__extension__=",
    "-D__restrict=",
    "-D__restrict__=",
    "-D__inline=static",
    "-D__inline__=static",
    "-D__volatile__=volatile",
    "-D__builtin_va_list=int",
    "-D__builtin_va_arg(ap,t)=__pesto_vaarg((ap),(t*)0)",
    "-D__asm__(x)=",
    "-D__asm(x)=",
]

PREAMBLE = """\
extern int __pesto_mutant_id;

extern int    __pesto_trap_neg_int (int    x);
extern int    __pesto_trap_pos_int (int    x);
extern int    __pesto_trap_zero_int(int    x);
extern double __pesto_trap_neg_dbl (double x);
extern double __pesto_trap_pos_dbl (double x);
extern double __pesto_trap_zero_dbl(double x);
extern void   __pesto_smtc(int limit);

#define __pesto_trap_neg(x)  _Generic((x), double: __pesto_trap_neg_dbl,  default: __pesto_trap_neg_int )(x)
#define __pesto_trap_pos(x)  _Generic((x), double: __pesto_trap_pos_dbl,  default: __pesto_trap_pos_int )(x)
#define __pesto_trap_zero(x) _Generic((x), double: __pesto_trap_zero_dbl, default: __pesto_trap_zero_int)(x)

"""

RUNTIME_C = """\
#include <stdlib.h>
#include <string.h>

int __pesto_mutant_id = -1;

__attribute__((constructor))
static void pesto_init(void) {
    const char *s = getenv("PESTO_MUTANT_ID");
    if (s && *s) {
        __pesto_mutant_id = (int)strtol(s, NULL, 10);
    }
}

int    __pesto_trap_neg_int (int    x) { if (x <  0)   abort(); return x; }
int    __pesto_trap_pos_int (int    x) { if (x >  0)   abort(); return x; }
int    __pesto_trap_zero_int(int    x) { if (x == 0)   abort(); return x; }
double __pesto_trap_neg_dbl (double x) { if (x <  0.0) abort(); return x; }
double __pesto_trap_pos_dbl (double x) { if (x >  0.0) abort(); return x; }
double __pesto_trap_zero_dbl(double x) { if (x == 0.0) abort(); return x; }

void __pesto_smtc(int limit) {
    static int count = 0;
    if (++count > limit) abort();
}
"""

ALL_MUTATION_TYPES = ["ORRN", "VTWD", "VDTR", "OASN", "OLBN", "SWDD", "SSDL", "Ccrc", "Ccrs", "SMTC"]
DEFAULT_MUTATION_TYPES = ["ORRN", "VTWD", "VDTR", "SSDL"]

_ORRN_OPS = frozenset({"<", "<=", ">", ">=", "==", "!="})
_ORRN_MUTATIONS = {
    "<":  ["<=", ">", ">=", "==", "!="],
    "<=": ["<",  ">", ">=", "==", "!="],
    ">":  ["<", "<=", ">=", "==", "!="],
    ">=": ["<", "<=", ">",  "==", "!="],
    "==": ["<", "<=", ">",  ">=", "!="],
    "!=": ["<", "<=", ">",  ">=", "=="],
}

_OASN_OPS = frozenset({"+", "-", "*", "/"})
_OASN_MUTATIONS = {op: ["<<", ">>"] for op in _OASN_OPS}

_OLBN_OPS = frozenset({"&&", "||"})
_OLBN_MUTATIONS = {"&&": ["&"], "||": ["|"]}

_INTEGER_PRIM_TYPES = frozenset({
    'int', 'long', 'short', 'char', 'unsigned', 'signed',
})
_FLOAT_PRIM_TYPES = frozenset({'float', 'double'})

_NUMERIC_CONST_TYPES = frozenset({
    'int', 'unsigned int', 'long', 'unsigned long',
    'long long', 'unsigned long long', 'float', 'double', 'long double',
})

_INTEGER_CONST_TYPES = frozenset({
    'int', 'unsigned int', 'long int', 'unsigned long int',
    'long long int', 'unsigned long long int', 'char',
})

_INT_RESULT_BINOPS = frozenset({
    '+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>',
})
_BOOL_RESULT_BINOPS = frozenset({'<', '<=', '>', '>=', '==', '!=', '&&', '||'})

_MAX_CONST_REPLACEMENTS = 3

_CHILD_LIST_RE = re.compile(r"^(\w+)\[(\d+)\]$")


def _parse_child_attr(name):
    m = _CHILD_LIST_RE.match(name)
    if m:
        return m.group(1), int(m.group(2))
    return name, None


def _id_check(mid):
    return c_ast.BinaryOp(
        op="==",
        left=c_ast.ID(name="__pesto_mutant_id"),
        right=c_ast.Constant(type="int", value=str(mid)),
    )


class ConstantCollector(c_ast.NodeVisitor):
    def __init__(self):
        self._global = {}
        self._func = {}
        self._current = None

    def visit_FuncDef(self, node):
        self._current = node.decl.name
        self._func.setdefault(self._current, {})
        self.generic_visit(node)
        self._current = None

    def visit_Constant(self, node):
        if node.type not in _NUMERIC_CONST_TYPES:
            return
        key = (node.type, node.value)
        self._global[key] = None
        if self._current is not None:
            self._func[self._current][key] = None

    def global_set(self):
        return list(self._global)

    def all_func_sets(self):
        return {name: list(keys) for name, keys in self._func.items()}


class MutationVisitor(c_ast.NodeVisitor):
    def __init__(self, scalar_typedefs=None, enabled=None,
                 global_consts=(), func_consts=None,
                 target_functions=None, id_offset=0, smtc_limit=None):
        self._counter = id_offset
        self._mutations = []
        self._scopes = [{}]
        self._suppress_scalar = False
        self._suppress_all = False
        self._scalar_typedefs = dict(scalar_typedefs) if scalar_typedefs is not None else {}
        self._enabled = set(enabled) if enabled is not None else set(DEFAULT_MUTATION_TYPES)
        self._global_consts = list(global_consts)
        self._func_consts = func_consts or {}
        self._current_func_name = None
        self._target_functions = target_functions  # None means all functions
        self._smtc_limit = smtc_limit if smtc_limit is not None else 1

    def _next_id(self, mutation_type, **info):
        n = self._counter
        self._counter += 1
        self._mutations.append({"id": n, "type": mutation_type, **info})
        return n

    def generic_visit(self, node):
        for child_name, child in node.children():
            new_child = self.visit(child)
            if new_child is not None and new_child is not child:
                attr, idx = _parse_child_attr(child_name)
                if idx is not None:
                    getattr(node, attr)[idx] = new_child
                else:
                    setattr(node, attr, new_child)
        return node

    def _kind_of_type(self, type_node):
        if isinstance(type_node, c_ast.TypeDecl) and isinstance(type_node.type, c_ast.IdentifierType):
            names = set(type_node.type.names)
            if names & _FLOAT_PRIM_TYPES:
                return 'float'
            if names & _INTEGER_PRIM_TYPES:
                return 'int'
            if names <= self._scalar_typedefs.keys():
                kinds = {self._scalar_typedefs[n] for n in names}
                return 'float' if 'float' in kinds else 'int'
        return 'other'

    # ORRN, OASN, OLBN
    def visit_BinaryOp(self, node):
        operands_integer = self._is_integer_expr(node.left) and self._is_integer_expr(node.right)
        self.generic_visit(node)
        if self._suppress_all:
            return node
        result = node
        if node.op in _ORRN_OPS and "ORRN" in self._enabled:
            for alt_op in _ORRN_MUTATIONS[node.op]:
                mid = self._next_id("ORRN", op=node.op, alt=alt_op)
                result = c_ast.TernaryOp(
                    cond=_id_check(mid),
                    iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                    iffalse=result,
                )
        if node.op in _OASN_OPS and "OASN" in self._enabled and operands_integer:
            for alt_op in _OASN_MUTATIONS[node.op]:
                mid = self._next_id("OASN", op=node.op, alt=alt_op)
                result = c_ast.TernaryOp(
                    cond=_id_check(mid),
                    iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                    iffalse=result,
                )
        if node.op in _OLBN_OPS and "OLBN" in self._enabled and operands_integer:
            for alt_op in _OLBN_MUTATIONS[node.op]:
                mid = self._next_id("OLBN", op=node.op, alt=alt_op)
                result = c_ast.TernaryOp(
                    cond=_id_check(mid),
                    iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                    iffalse=result,
                )
        return result

    # SMTC
    def _inject_loop_abort(self, node):
        if "SMTC" not in self._enabled or self._suppress_all:
            return
        mid = self._next_id("SMTC", limit=self._smtc_limit)
        guard = c_ast.If(
            cond=_id_check(mid),
            iftrue=c_ast.FuncCall(
                name=c_ast.ID(name="__pesto_smtc"),
                args=c_ast.ExprList(exprs=[
                    c_ast.Constant(type="int", value=str(self._smtc_limit)),
                ]),
            ),
            iffalse=None,
        )
        body = node.stmt
        if isinstance(body, c_ast.Compound):
            body.block_items = [guard] + (body.block_items or [])
        else:
            body_items = [guard] + ([body] if body is not None else [])
            node.stmt = c_ast.Compound(block_items=body_items)

    # SWDD + SMTC
    def visit_While(self, node):
        self.generic_visit(node)
        self._inject_loop_abort(node)
        if "SWDD" not in self._enabled:
            return node
        mid = self._next_id("SWDD")
        do_while = c_ast.DoWhile(cond=deepcopy(node.cond), stmt=deepcopy(node.stmt))
        return c_ast.If(cond=_id_check(mid), iftrue=do_while, iffalse=node)

    # SMTC
    def visit_For(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        self._inject_loop_abort(node)
        self._scopes.pop()
        return node

    # SMTC
    def visit_DoWhile(self, node):
        self.generic_visit(node)
        self._inject_loop_abort(node)
        return node

    def visit_FuncDecl(self, node):
        return node

    def visit_ArrayDecl(self, node):
        old, self._suppress_all = self._suppress_all, True
        self.generic_visit(node)
        self._suppress_all = old
        return node

    # SSDL + scope management
    def visit_Compound(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        if "SSDL" in self._enabled and node.block_items:
            new_items = []
            for stmt in node.block_items:
                if isinstance(stmt, c_ast.Decl):
                    new_items.append(stmt)
                else:
                    mid = self._next_id("SSDL")
                    new_items.append(c_ast.If(
                        cond=_id_check(mid),
                        iftrue=c_ast.Compound(block_items=None),
                        iffalse=stmt,
                    ))
            node.block_items = new_items
        self._scopes.pop()
        return node

    def _kind_of_name(self, name):
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def _is_scalar(self, name):
        return self._kind_of_name(name) in ('int', 'float')

    def _is_integer(self, name):
        return self._kind_of_name(name) == 'int'

    def _is_integer_expr(self, node):
        if isinstance(node, c_ast.Constant):
            return node.type in _INTEGER_CONST_TYPES
        if isinstance(node, c_ast.ID):
            return self._is_integer(node.name)
        if isinstance(node, c_ast.Cast):
            return self._kind_of_type(getattr(node.to_type, 'type', None)) == 'int'
        if isinstance(node, c_ast.UnaryOp):
            if node.op in ('~', '!', 'sizeof'):
                return True
            if node.op in ('-', '+'):
                return self._is_integer_expr(node.expr)
            return False
        if isinstance(node, c_ast.BinaryOp):
            if node.op in _BOOL_RESULT_BINOPS:
                return True
            if node.op in _INT_RESULT_BINOPS:
                return self._is_integer_expr(node.left) and self._is_integer_expr(node.right)
            return False
        if isinstance(node, c_ast.TernaryOp):
            return (self._is_integer_expr(node.iftrue)
                    and self._is_integer_expr(node.iffalse))
        return False

    def _visit_suppressed(self, node):
        old, self._suppress_scalar = self._suppress_scalar, True
        result = self.visit(node)
        self._suppress_scalar = old
        return result

    def _twiddle(self, node):
        result = node
        for op in ['-', '+']:
            mid = self._next_id("VTWD", delta=op + "1")
            result = c_ast.TernaryOp(
                cond=_id_check(mid),
                iftrue=c_ast.BinaryOp(op=op, left=deepcopy(node),
                                      right=c_ast.Constant(type='int', value='1')),
                iffalse=result,
            )
        return result

    def _domain_trap(self, original, outer):
        result = outer
        for trap in ['__pesto_trap_neg', '__pesto_trap_pos', '__pesto_trap_zero']:
            mid = self._next_id("VDTR", trap=trap)
            result = c_ast.TernaryOp(
                cond=_id_check(mid),
                iftrue=c_ast.FuncCall(
                    name=c_ast.ID(name=trap),
                    args=c_ast.ExprList(exprs=[deepcopy(original)]),
                ),
                iffalse=result,
            )
        return result

    def _ternary_chain(self, result, alts, mutation_type):
        for alt in alts:
            mid = self._next_id(mutation_type)
            result = c_ast.TernaryOp(_id_check(mid), alt, result)
        return result

    # Ccrc
    def _cccr(self, node, key, int_only):
        local = self._func_consts.get(self._current_func_name, [])
        local_set = set(local)

        def usable(t):
            return (t in _INTEGER_CONST_TYPES) if int_only else True

        alts = (
            [c_ast.Constant(type=t, value=v) for t, v in local
             if (t, v) != key and usable(t)]
            + [c_ast.Constant(type=t, value=v) for t, v in self._global_consts
               if (t, v) != key and (t, v) not in local_set and usable(t)]
        )
        return self._ternary_chain(node, alts[:_MAX_CONST_REPLACEMENTS], "Ccrc")

    # Ccrs
    def _ccsr(self, result, int_only):
        want = ('int',) if int_only else ('int', 'float')
        seen = set()
        alts = []
        for scope in self._scopes[1:] + self._scopes[:1]:
            for name, kind in scope.items():
                if kind in want and name not in seen:
                    alts.append(c_ast.ID(name=name))
                    seen.add(name)
        return self._ternary_chain(result, alts[:_MAX_CONST_REPLACEMENTS], "Ccrs")

    def visit_Struct(self, node):
        return node

    def visit_Union(self, node):
        return node

    def visit_Enum(self, node):
        return node

    def visit_Typedef(self, node):
        if (isinstance(node.type, c_ast.TypeDecl) and
                isinstance(node.type.type, c_ast.IdentifierType)):
            kind = self._kind_of_type(node.type)
            if kind in ('int', 'float'):
                self._scalar_typedefs[node.name] = kind
        return node

    def visit_Decl(self, node):
        if 'typedef' not in (node.storage or []):
            self._scopes[-1][node.name] = self._kind_of_type(node.type)
        static_storage = (
            self._current_func_name is None or 'static' in (node.storage or [])
        )
        if static_storage:
            old, self._suppress_all = self._suppress_all, True
            self.generic_visit(node)
            self._suppress_all = old
        else:
            self.generic_visit(node)
        return node

    def visit_Assignment(self, node):
        new_rvalue = self.visit(node.rvalue)
        if new_rvalue is not node.rvalue:
            node.rvalue = new_rvalue
        self._visit_suppressed(node.lvalue)
        return node

    def visit_FuncCall(self, node):
        node.name = self._visit_suppressed(node.name)
        if node.args:
            new_args = self.visit(node.args)
            if new_args is not node.args:
                node.args = new_args
        return node

    def visit_StructRef(self, node):
        new_name = self.visit(node.name)
        if new_name is not node.name:
            node.name = new_name
        return node

    def visit_ArrayRef(self, node):
        self._visit_suppressed(node.name)
        node.subscript = self.visit(node.subscript)
        return node

    def visit_UnaryOp(self, node):
        if node.op in ['p++', 'p--', '++', '--']:
            self._visit_suppressed(node.expr)
            return node
        if node.op == '&':
            self._visit_suppressed(node.expr)
            return node
        if node.op == '*':
            self._visit_suppressed(node.expr)
            return node
        self.generic_visit(node)
        return node

    def visit_Case(self, node):
        if node.expr is not None:
            old, self._suppress_all = self._suppress_all, True
            self.visit(node.expr)
            self._suppress_all = old
        for i, stmt in enumerate(node.stmts or []):
            new = self.visit(stmt)
            if new is not None and new is not stmt:
                node.stmts[i] = new
        return node

    # VTWD + VDTR
    def visit_ID(self, node):
        if self._suppress_all or self._suppress_scalar or not self._is_scalar(node.name):
            return node
        result = node
        if "VTWD" in self._enabled:
            result = self._twiddle(result)
        if "VDTR" in self._enabled:
            result = self._domain_trap(node, result)
        return result

    # Ccrc + Ccrs
    def visit_Constant(self, node):
        if self._suppress_all or self._suppress_scalar or node.type not in _NUMERIC_CONST_TYPES:
            return node
        result = node
        key = (node.type, node.value)
        int_only = node.type in _INTEGER_CONST_TYPES
        if "Ccrc" in self._enabled:
            result = self._cccr(result, key, int_only)
        if "Ccrs" in self._enabled:
            result = self._ccsr(result, int_only)
        return result

    def _register_params(self, decl):
        ft = decl.type
        if not isinstance(ft, c_ast.FuncDecl) or ft.args is None:
            return
        for p in ft.args.params:
            if isinstance(p, c_ast.Decl) and p.name:
                self._scopes[-1][p.name] = self._kind_of_type(p.type)

    def visit_FuncDef(self, node):
        func_name = node.decl.name
        if self._target_functions is not None and func_name not in self._target_functions:
            return node
        self._current_func_name = func_name
        self._scopes.append({})
        self._register_params(node.decl)
        self.generic_visit(node)
        self._scopes.pop()
        self._current_func_name = None
        return node


def _collect_scalar_typedefs(tree):
    scalar = {}

    class _Tracker(c_ast.NodeVisitor):
        def visit_Typedef(self, node):
            name = node.name
            if name.startswith('__') and any(c.isdigit() for c in name):
                return
            if (isinstance(node.type, c_ast.TypeDecl) and
                    isinstance(node.type.type, c_ast.IdentifierType)):
                names = set(node.type.type.names)
                if names & _FLOAT_PRIM_TYPES:
                    scalar[name] = 'float'
                elif names & _INTEGER_PRIM_TYPES:
                    scalar[name] = 'int'
                elif names <= scalar.keys():
                    kinds = {scalar[n] for n in names}
                    scalar[name] = 'float' if 'float' in kinds else 'int'

    _Tracker().visit(tree)
    return scalar


_FOOTER_TRIGGERS = (
    '"stringlib/asciilib', '"stringlib/ucs1lib',
    '"stringlib/ucs2lib', '"stringlib/ucs4lib',
)
_ALWAYS_HEADER = (
    '"stringlib/localeutil', '"stringlib/eq',
)
_NEVER_EXTRACT = (
    '"generated_cases.c.h"',
    '"executor_cases.c.h"',
)


def _extract_includes(c_file):
    src_lines = Path(c_file).read_text().splitlines()
    header, footer = [], []
    in_template_block = False

    def is_trigger(stripped):
        return stripped.startswith('#include') and any(
            pat in stripped for pat in _FOOTER_TRIGGERS
        )

    def is_always_hdr(stripped):
        return stripped.startswith('#include') and any(
            pat in stripped for pat in _ALWAYS_HEADER
        )

    i = 0
    while i < len(src_lines):
        line = src_lines[i]
        stripped = line.strip()

        if stripped.startswith(('#if ', '#ifdef', '#ifndef', '#if\t')):
            block = []
            block_depth = 0
            j = i
            while j < len(src_lines):
                bline = src_lines[j]
                bstripped = bline.strip()
                if bstripped.startswith(('#if ', '#ifdef', '#ifndef', '#if\t')):
                    block_depth += 1
                elif bstripped.startswith('#endif'):
                    block_depth -= 1
                block.append(bline)
                j += 1
                if block_depth == 0:
                    break

            has_define = any(
                bl.strip().startswith(('#define', '#undef')) for bl in block
            )
            if has_define:
                dest = footer if in_template_block else header
                dest.extend(block)
            i = j
            continue

        elif stripped.startswith(('#define', '#undef')):
            # Multi-line define: gather continuation lines
            block = [line]
            while block[-1].rstrip().endswith('\\') and i + len(block) < len(src_lines):
                block.append(src_lines[i + len(block)])
            i += len(block)
            dest = footer if in_template_block else header
            dest.extend(block)
            continue

        elif stripped.startswith('#include'):
            if any(pat in stripped for pat in _NEVER_EXTRACT):
                pass 
            elif is_always_hdr(stripped):
                in_template_block = False
                header.append(line)
            elif is_trigger(stripped):
                in_template_block = True
                footer.append(line)
            elif in_template_block:
                footer.append(line)
            else:
                header.append(line)

        i += 1

    return '\n'.join(header) + '\n', '\n'.join(footer) + '\n'


_VAARG_RE = re.compile(r'__pesto_vaarg\((.+?),\s*\((.+?)\)\s*0\)')


def _restore_va_arg(code):
    """Turn the __pesto_vaarg(...) markers (see DEFAULT_CPP_ARGS) back into real
    va_arg() calls.  The marker is ``__pesto_vaarg((ap), (T *) 0)`` where ``T``
    is the original va_arg type with one extra ``*`` appended; we drop that
    trailing ``*`` to recover the type."""
    def repl(m):
        ap = m.group(1).strip()
        cast = m.group(2).strip()
        t = cast[:-1].rstrip() if cast.endswith('*') else cast
        return f'va_arg({ap}, {t})'
    return _VAARG_RE.sub(repl, code)


def _decl_name(node):
    if isinstance(node, c_ast.FuncDef):
        return node.decl.name if node.decl else None
    if isinstance(node, (c_ast.Decl, c_ast.Typedef)):
        return node.name
    return None


def mutate_file(c_file, cpp_path="gcc", cpp_args=None, include_paths=None,
                enabled_mutations=None, target_functions=None, id_offset=0,
                smtc_limit=None):
    args = list(DEFAULT_CPP_ARGS)
    if include_paths:
        args.extend(f"-I{p}" for p in include_paths)
    if cpp_args:
        args.extend(cpp_args)

    c_file = str(Path(c_file).resolve())
    tree = pycparser.parse_file(c_file, use_cpp=True, cpp_path=cpp_path, cpp_args=args)

    scalar_typedefs = _collect_scalar_typedefs(tree)
    target_path = c_file

    other_decls  = [d for d in tree.ext if not (d.coord and str(d.coord.file) == target_path)]
    target_decls = [d for d in tree.ext if      d.coord and str(d.coord.file) == target_path]

    header_func_defs = {_decl_name(d) for d in other_decls if isinstance(d, c_ast.FuncDef)} - {None}

    _define_re = re.compile(r'^\s*#define\s+(\w+)(?![\w(])')
    define_names = set()
    for line in Path(c_file).read_text().splitlines():
        m = _define_re.match(line)
        if m:
            define_names.add(m.group(1))

    target_decls = [
        d for d in target_decls
        if not (isinstance(d, c_ast.FuncDef) and
                (_decl_name(d) in header_func_defs or _decl_name(d) in define_names))
    ]
    tree.ext = target_decls

    enabled = set(enabled_mutations) if enabled_mutations is not None else set(DEFAULT_MUTATION_TYPES)

    global_consts, func_consts = (), {}
    if "Ccrc" in enabled or "Ccrs" in enabled:
        collector = ConstantCollector()
        collector.visit(tree)
        global_consts = collector.global_set()
        func_consts = collector.all_func_sets()

    target_func_set = set(target_functions) if target_functions is not None else None

    visitor = MutationVisitor(
        scalar_typedefs=scalar_typedefs,
        enabled=enabled,
        global_consts=global_consts,
        func_consts=func_consts,
        target_functions=target_func_set,
        id_offset=id_offset,
        smtc_limit=smtc_limit,
    )
    visitor.visit(tree)

    code = c_generator.CGenerator().visit(tree)
    code = _restore_va_arg(code)
    header_includes, footer_includes = _extract_includes(c_file)

    gen = c_generator.CGenerator()
    forward_decls = []

    seen_structs: set = set()
    for d in target_decls:
        cands = []
        if isinstance(d, c_ast.Decl):
            cands.append(d.type)
        elif isinstance(d, c_ast.FuncDef) and d.decl:
            cands.append(d.decl.type)
        for t in cands:
            while isinstance(t, (c_ast.PtrDecl, c_ast.TypeDecl)):
                t = t.type
            if isinstance(t, c_ast.Struct) and t.name and t.name not in seen_structs:
                forward_decls.append(f'struct {t.name};')
                seen_structs.add(t.name)

    local_typedefs = {
        d.name for d in target_decls
        if isinstance(d, c_ast.Typedef)
    }
    local_structs = seen_structs
    for d in target_decls:
        if not isinstance(d, c_ast.FuncDef):
            continue
        decl = d.decl
        if 'static' not in (decl.storage or []):
            continue
        try:
            decl_text = gen.visit(decl) + ';'
        except Exception:
            continue
        if any(t in decl_text for t in local_typedefs | local_structs):
            continue
        forward_decls.append(decl_text)

    _TEMPLATE_HDR_PATTERNS = (
        'asciilib', 'ucs1lib', 'ucs2lib', 'ucs4lib', 'fastsearch',
        'partition', 'split', 'count', 'find', 'replace', 'codecs',
        'find_max_char', 'transmogrify',
    )
    if footer_includes:
        for d in other_decls:
            if not (isinstance(d, c_ast.FuncDef) and d.coord):
                continue
            f = str(d.coord.file)
            if 'stringlib' not in f:
                continue
            if not any(pat in f for pat in _TEMPLATE_HDR_PATTERNS):
                continue
            func_name = _decl_name(d)
            if func_name is None:
                continue
            try:
                decl_text = gen.visit(d.decl) + ';'
            except Exception:
                continue
            if 'prework' in decl_text:
                continue
            forward_decls.append(decl_text)

    diag = (
        '#pragma GCC diagnostic ignored "-Wunused-variable"\n'
        '#pragma GCC diagnostic ignored "-Wunused-function"\n'
        '#pragma GCC diagnostic ignored "-Wmissing-field-initializers"\n'
    )
    fwd_section = '\n'.join(forward_decls) + '\n' if forward_decls else ''

    header_lines = header_includes.splitlines(keepends=True)
    early_includes, late_includes = [], []
    seen_late = False
    for hl in header_lines:
        s = hl.strip()
        if s.startswith('#include') and not (
            '"Python.h"' in s or '<Python.h>' in s
            or '"pycore_' in s or '"cpython/' in s
            or '<std' in s or '<errno' in s or '<assert' in s
            or '<wchar' in s or '<limits' in s or '<ctype' in s
            or '"bytesobject.h"' in s or '"tupleobject.h"' in s
        ):
            seen_late = True
        (late_includes if seen_late else early_includes).append(hl)
    early_hdr = ''.join(early_includes)
    late_hdr = ''.join(late_includes)

    mutation_count = visitor._counter - id_offset
    return (
        PREAMBLE + early_hdr + fwd_section + late_hdr + diag + code + footer_includes,
        RUNTIME_C, mutation_count, visitor._mutations,
    )
