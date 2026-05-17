import re
from copy import deepcopy
from pathlib import Path

import pycparser
import pycparser.c_ast as c_ast
from pycparser import c_generator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CPYTHON_ROOT = PROJECT_ROOT / "vendor" / "cpython"

CPYTHON_HEADERS = Path(__file__).parent / "cpython_headers"

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
    "-D__typeof__(...)=int",
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

_ORRN_OPS = frozenset({"<", "<=", ">", ">=", "==", "!="})
_ORRN_MUTATIONS = {
    "<":  ["<=", ">", ">=", "==", "!="],
    "<=": ["<",  ">", ">=", "==", "!="],
    ">":  ["<", "<=", ">=", "==", "!="],
    ">=": ["<", "<=", ">",  "==", "!="],
    "==": ["<", "<=", ">",  ">=", "!="],
    "!=": ["<", "<=", ">",  ">=", "=="],
}

_PRIMITIVE_INT_TYPES = frozenset({
    'int', 'long', 'short', 'char', 'unsigned', 'signed',
    'float', 'double',
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


class MutationVisitor(c_ast.NodeVisitor):
    def __init__(self, scalar_typedefs=None):
        self._counter = 0
        self._mutations = []
        self._scopes = [{}]
        self._suppress_scalar = False
        self._scalar_typedefs = scalar_typedefs if scalar_typedefs is not None else set()

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

    # ORRN
    def visit_BinaryOp(self, node):
        self.generic_visit(node)
        if node.op not in _ORRN_OPS:
            return node
        alternatives = _ORRN_MUTATIONS.get(node.op, [])
        result = node
        for alt_op in alternatives:
            mid = self._next_id("ORRN", op=node.op, alt=alt_op)
            result = c_ast.TernaryOp(
                cond=_id_check(mid),
                iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                iffalse=result,
            )
        return result

    def visit_Compound(self, node):
        self._scopes.append({})
        self.generic_visit(node)
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
        return self._domain_trap(node, self._twiddle(node))

    def visit_FuncDef(self, node):
        self._scopes.append({})
        self.generic_visit(node)
        self._scopes.pop()
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


def mutate_file(c_file, cpp_path="gcc", cpp_args=None, include_paths=None):
    args = list(DEFAULT_CPP_ARGS)
    if include_paths:
        args.extend(f"-I{p}" for p in include_paths)
    if cpp_args:
        args.extend(cpp_args)

    tree = pycparser.parse_file(c_file, use_cpp=True, cpp_path=cpp_path, cpp_args=args)

    scalar_typedefs = _collect_scalar_typedefs(tree)
    target_path = str(Path(c_file).resolve())

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

    visitor = MutationVisitor(scalar_typedefs=scalar_typedefs)
    visitor.visit(tree)

    code = c_generator.CGenerator().visit(tree)
    includes = _extract_includes(c_file)
    diag = (
        '#pragma GCC diagnostic ignored "-Wunused-variable"\n'
        '#pragma GCC diagnostic ignored "-Wunused-function"\n'
        '#pragma GCC diagnostic ignored "-Wmissing-field-initializers"\n'
    )
    return PREAMBLE + includes + diag + code, RUNTIME_C, visitor._counter, visitor._mutations
