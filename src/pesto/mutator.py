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
"""

ALL_MUTATION_TYPES = ["ORRN", "VTWD", "VDTR", "OASN", "OLBN", "SWDD", "SSDL", "Ccrc", "Ccrs"]
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

_PRIMITIVE_INT_TYPES = frozenset({
    'int', 'long', 'short', 'char', 'unsigned', 'signed',
    'float', 'double',
})

_NUMERIC_CONST_TYPES = frozenset({
    'int', 'unsigned int', 'long', 'unsigned long',
    'long long', 'unsigned long long', 'float', 'double', 'long double',
})

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
                 target_functions=None, id_offset=0):
        self._counter = id_offset
        self._mutations = []
        self._scopes = [{}]
        self._suppress_scalar = False
        self._scalar_typedefs = scalar_typedefs if scalar_typedefs is not None else set()
        self._enabled = set(enabled) if enabled is not None else set(DEFAULT_MUTATION_TYPES)
        self._global_consts = list(global_consts)
        self._func_consts = func_consts or {}
        self._current_func_name = None
        self._target_functions = target_functions  # None means all functions

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

    def _is_scalar_type(self, type_node):
        if isinstance(type_node, c_ast.TypeDecl):
            if isinstance(type_node.type, c_ast.IdentifierType):
                names = set(type_node.type.names)
                if names & _PRIMITIVE_INT_TYPES:
                    return True
                if names <= self._scalar_typedefs:
                    return True
        return False

    # ORRN, OASN, OLBN
    def visit_BinaryOp(self, node):
        self.generic_visit(node)
        result = node
        if node.op in _ORRN_OPS and "ORRN" in self._enabled:
            for alt_op in _ORRN_MUTATIONS[node.op]:
                mid = self._next_id("ORRN", op=node.op, alt=alt_op)
                result = c_ast.TernaryOp(
                    cond=_id_check(mid),
                    iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                    iffalse=result,
                )
        if node.op in _OASN_OPS and "OASN" in self._enabled:
            for alt_op in _OASN_MUTATIONS[node.op]:
                mid = self._next_id("OASN", op=node.op, alt=alt_op)
                result = c_ast.TernaryOp(
                    cond=_id_check(mid),
                    iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                    iffalse=result,
                )
        if node.op in _OLBN_OPS and "OLBN" in self._enabled:
            for alt_op in _OLBN_MUTATIONS[node.op]:
                mid = self._next_id("OLBN", op=node.op, alt=alt_op)
                result = c_ast.TernaryOp(
                    cond=_id_check(mid),
                    iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                    iffalse=result,
                )
        return result

    # SWDD
    def visit_While(self, node):
        self.generic_visit(node)
        if "SWDD" not in self._enabled:
            return node
        mid = self._next_id("SWDD")
        do_while = c_ast.DoWhile(cond=deepcopy(node.cond), stmt=deepcopy(node.stmt))
        return c_ast.If(cond=_id_check(mid), iftrue=do_while, iffalse=node)

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

    def _is_scalar(self, name):
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
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
    def _cccr(self, node, key):
        local = self._func_consts.get(self._current_func_name, [])
        local_set = set(local)
        alts = (
            [c_ast.Constant(type=t, value=v) for t, v in local if (t, v) != key]
            + [c_ast.Constant(type=t, value=v) for t, v in self._global_consts
               if (t, v) != key and (t, v) not in local_set]
        )
        return self._ternary_chain(node, alts, "Ccrc")

    # Ccrs
    def _ccsr(self, result):
        seen = set()
        alts = []
        for scope in self._scopes[1:] + self._scopes[:1]:
            for name, is_scalar in scope.items():
                if is_scalar and name not in seen:
                    alts.append(c_ast.ID(name=name))
                    seen.add(name)
        return self._ternary_chain(result, alts, "Ccrs")

    def visit_Struct(self, node):
        return node

    def visit_Union(self, node):
        return node

    def visit_Enum(self, node):
        return node

    def visit_Typedef(self, node):
        if (isinstance(node.type, c_ast.TypeDecl) and
                isinstance(node.type.type, c_ast.IdentifierType)):
            names = set(node.type.type.names)
            if names & _PRIMITIVE_INT_TYPES or names <= self._scalar_typedefs:
                self._scalar_typedefs.add(node.name)
        return node

    def visit_Decl(self, node):
        if 'typedef' not in (node.storage or []):
            is_scalar = self._is_scalar_type(node.type)
            self._scopes[-1][node.name] = is_scalar
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

    # VTWD + VDTR
    def visit_ID(self, node):
        if self._suppress_scalar or not self._is_scalar(node.name):
            return node
        result = node
        if "VTWD" in self._enabled:
            result = self._twiddle(result)
        if "VDTR" in self._enabled:
            result = self._domain_trap(node, result)
        return result

    # Ccrc + Ccrs
    def visit_Constant(self, node):
        if self._suppress_scalar or node.type not in _NUMERIC_CONST_TYPES:
            return node
        result = node
        key = (node.type, node.value)
        if "Ccrc" in self._enabled:
            result = self._cccr(result, key)
        if "Ccrs" in self._enabled:
            result = self._ccsr(result)
        return result

    def visit_FuncDef(self, node):
        func_name = node.decl.name
        if self._target_functions is not None and func_name not in self._target_functions:
            return node
        self._current_func_name = func_name
        self._scopes.append({})
        self.generic_visit(node)
        self._scopes.pop()
        self._current_func_name = None
        return node


def _collect_scalar_typedefs(tree):
    scalar = set()

    class _Tracker(c_ast.NodeVisitor):
        def visit_Typedef(self, node):
            name = node.name
            if name.startswith('__') and any(c.isdigit() for c in name):
                return
            if (isinstance(node.type, c_ast.TypeDecl) and
                    isinstance(node.type.type, c_ast.IdentifierType)):
                names = set(node.type.type.names)
                if names & _PRIMITIVE_INT_TYPES or names <= scalar:
                    scalar.add(name)

    _Tracker().visit(tree)
    return scalar


def _extract_includes(c_file):
    lines = []
    for line in Path(c_file).read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith('#include'):
            lines.append(line)
    return '\n'.join(lines) + '\n'


def _decl_name(node):
    if isinstance(node, c_ast.FuncDef):
        return node.decl.name if node.decl else None
    if isinstance(node, (c_ast.Decl, c_ast.Typedef)):
        return node.name
    return None


def mutate_file(c_file, cpp_path="gcc", cpp_args=None, include_paths=None,
                enabled_mutations=None, target_functions=None, id_offset=0):
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

    _undef_re = re.compile(r'^\s*#undef\s+(\w+)')
    undef_names = set()
    for line in Path(c_file).read_text().splitlines():
        m = _undef_re.match(line)
        if m:
            undef_names.add(m.group(1))

    target_decls = [
        d for d in target_decls
        if not (isinstance(d, c_ast.FuncDef) and
                (_decl_name(d) in header_func_defs or _decl_name(d) in undef_names))
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
    )
    visitor.visit(tree)

    code = c_generator.CGenerator().visit(tree)
    includes = _extract_includes(c_file)
    diag = (
        '#pragma GCC diagnostic ignored "-Wunused-variable"\n'
        '#pragma GCC diagnostic ignored "-Wunused-function"\n'
        '#pragma GCC diagnostic ignored "-Wmissing-field-initializers"\n'
    )
    mutation_count = visitor._counter - id_offset
    return PREAMBLE + includes + diag + code, RUNTIME_C, mutation_count, visitor._mutations
