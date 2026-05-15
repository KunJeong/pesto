import re
from copy import deepcopy

import pycparser
import pycparser.c_ast as c_ast
from pycparser import c_generator

BINARY_MUTATIONS = {
    # OASN
    "+":  ["<<", ">>"], "-":  ["<<", ">>"], "*":  ["<<", ">>"], "/":  ["<<", ">>"],
    # ORRN
    "<":  ["<=", ">", ">=", "==", "!="],
    "<=": ["<",  ">", ">=", "==", "!="],
    ">":  ["<", "<=", ">=", "==", "!="],
    ">=": ["<", "<=", ">",  "==", "!="],
    "==": ["<", "<=", ">",  ">=", "!="],
    "!=": ["<", "<=", ">",  ">=", "=="],
    # OLBN
    "&&": ["&"], "||": ["|"],
}

_NUMERIC_CONST_TYPES = frozenset({
    'int', 'unsigned int', 'long', 'unsigned long',
    'long long', 'unsigned long long',
    'float', 'double', 'long double',
})

DEFAULT_CPP_ARGS = [
    "-E",
    "-P",
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
#include <stdio.h>
#include <stdlib.h>

int __pesto_mutant_id = -1;

__attribute__((constructor))
static void pesto_init(void) {
    scanf("%d", &__pesto_mutant_id);
}

int    __pesto_trap_neg_int (int    x) { if (x <  0)   abort(); return x; }
int    __pesto_trap_pos_int (int    x) { if (x >  0)   abort(); return x; }
int    __pesto_trap_zero_int(int    x) { if (x == 0)   abort(); return x; }
double __pesto_trap_neg_dbl (double x) { if (x <  0.0) abort(); return x; }
double __pesto_trap_pos_dbl (double x) { if (x >  0.0) abort(); return x; }
double __pesto_trap_zero_dbl(double x) { if (x == 0.0) abort(); return x; }
"""

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
    def __init__(self, global_consts=(), func_consts=None):
        self._counter = 0
        self._scopes = [{}]
        self._suppress_scalar = False
        self._global_consts = list(global_consts)
        self._func_consts = func_consts or {}
        self._current_func_name = None

    # Helper functions
    def _next_id(self):
        n = self._counter
        self._counter += 1
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

    # SWDD
    def visit_While(self, node): 
        self.generic_visit(node)
        mid = self._next_id()
        do_while = c_ast.DoWhile(cond=deepcopy(node.cond), stmt=deepcopy(node.stmt))
        return c_ast.If(cond=_id_check(mid), iftrue=do_while, iffalse=node)

    # OASN, ORRN, OLBN
    def visit_BinaryOp(self, node): 
        self.generic_visit(node)
        alternatives = BINARY_MUTATIONS.get(node.op)
        if not alternatives:
            return node
        result = node
        for alt_op in alternatives:
            mid = self._next_id()
            result = c_ast.TernaryOp(
                cond=_id_check(mid),
                iftrue=c_ast.BinaryOp(op=alt_op, left=deepcopy(node.left), right=deepcopy(node.right)),
                iffalse=result,
            )
        return result

    # SSDL + scope management
    def visit_Compound(self, node): 
        self._scopes.append({})
        self.generic_visit(node)
        if node.block_items:
            new_items = []
            for stmt in node.block_items:
                if isinstance(stmt, c_ast.Decl):
                    new_items.append(stmt)
                else:
                    mid = self._next_id()
                    new_items.append(
                        c_ast.If(
                            cond=_id_check(mid),
                            iftrue=c_ast.Compound(block_items=None),
                            iffalse=stmt,
                        )
                    )
            node.block_items = new_items
        self._scopes.pop()
        return node
    
    # VTWD, VDTR
    def _is_scalar(self, name):
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return True

    def _visit_suppressed(self, node):
        old, self._suppress_scalar = self._suppress_scalar, True
        result = self.visit(node)
        self._suppress_scalar = old
        return result

    def _twiddle(self, node):
        result = node
        for op in ['-', '+']:
            mid = self._next_id()
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
            mid = self._next_id()
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

    def visit_Decl(self, node):
        if 'typedef' not in (node.storage or []):
            is_scalar = (
                isinstance(node.type, c_ast.TypeDecl) and
                isinstance(node.type.type, c_ast.IdentifierType)
            )
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

    def visit_UnaryOp(self, node):
        if node.op in ['p++', 'p--', '++', '--']:
            self._visit_suppressed(node.expr)
            return node
        if node.op == '*':
            was_suppressed = self._suppress_scalar
            self._suppress_scalar = True
            self.generic_visit(node)
            self._suppress_scalar = was_suppressed
            if was_suppressed:
                return node
            return self._domain_trap(node, self._twiddle(node))
        self.generic_visit(node)
        return node
    
    # VTWD + VDTR
    def visit_ID(self, node):
        if self._suppress_scalar or not self._is_scalar(node.name):
            return node
        return self._domain_trap(node, self._twiddle(node))
    
    def visit_FuncDef(self, node):
        self._current_func_name = node.decl.name
        self._scopes.append({})
        self.generic_visit(node)
        self._scopes.pop()
        self._current_func_name = None
        return node

    def _ternary_chain(self, result, alts):
        for alt in alts:
            mid = self._next_id()
            result = c_ast.TernaryOp(_id_check(mid), alt, result)
        return result

    # Cccr
    def _cccr(self, node, key):
        local = self._func_consts.get(self._current_func_name, [])
        local_set = set(local)
        alts = (
            [c_ast.Constant(type=t, value=v) for t, v in local if (t, v) != key]
            + [c_ast.Constant(type=t, value=v) for t, v in self._global_consts if (t, v) != key and (t, v) not in local_set]
        )
        return self._ternary_chain(node, alts)

    # Ccsr
    def _ccsr(self, result):
        seen = set()
        alts = []
        for scope in self._scopes[1:] + self._scopes[:1]:
            for name, is_scalar in scope.items():
                if is_scalar and name not in seen:
                    alts.append(c_ast.ID(name=name))
                    seen.add(name)
        return self._ternary_chain(result, alts)

    def visit_Constant(self, node):
        if self._suppress_scalar or node.type not in _NUMERIC_CONST_TYPES:
            return node
        key = (node.type, node.value)
        return self._ccsr(self._cccr(node, key))


def mutate_file(c_file, cpp_path="gcc", cpp_args=None, include_paths=None):
    args = list(DEFAULT_CPP_ARGS)
    if include_paths:
        args.extend(f"-I{p}" for p in include_paths)
    if cpp_args:
        args.extend(cpp_args)

    tree = pycparser.parse_file(c_file, use_cpp=True, cpp_path=cpp_path, cpp_args=args)

    collector = ConstantCollector()
    collector.visit(tree)

    visitor = MutationVisitor(
        global_consts=collector.global_set(),
        func_consts=collector.all_func_sets(),
    )
    visitor.visit(tree)

    code = c_generator.CGenerator().visit(tree)
    return PREAMBLE + code, RUNTIME_C
