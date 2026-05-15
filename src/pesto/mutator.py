import re
from copy import deepcopy

import pycparser
import pycparser.c_ast as c_ast
from pycparser import c_generator

BINARY_MUTATIONS = {
    # OASN (Arithmetic Operator by Shift Operator)
    "+":  ["<<", ">>"], "-":  ["<<", ">>"], "*":  ["<<", ">>"], "/":  ["<<", ">>"],
    # ORRN (Relational Operator Mutation)
    "<":  ["<=", ">", ">=", "==", "!="],
    "<=": ["<",  ">", ">=", "==", "!="],
    ">":  ["<", "<=", ">=", "==", "!="],
    ">=": ["<", "<=", ">",  "==", "!="],
    "==": ["<", "<=", ">",  ">=", "!="],
    "!=": ["<", "<=", ">",  ">=", "=="],
    # OLBN (Logical Operator by Bitwise Operator)
    "&&": ["&"], "||": ["|"],
}

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


class MutationVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self._counter = 0
        self._scopes = [{}]          # [{name: is_scalar}] — symbol table stack
        self._suppress_scalar = False

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
    
    def visit_ID(self, node):
        if self._suppress_scalar or not self._is_scalar(node.name):
            return node
        return self._domain_trap(node, self._twiddle(node))


def mutate_file(c_file, cpp_path="gcc", cpp_args=None, include_paths=None):
    args = list(DEFAULT_CPP_ARGS)
    if include_paths:
        args.extend(f"-I{p}" for p in include_paths)
    if cpp_args:
        args.extend(cpp_args)

    tree = pycparser.parse_file(c_file, use_cpp=True, cpp_path=cpp_path, cpp_args=args)

    visitor = MutationVisitor()
    visitor.visit(tree)

    code = c_generator.CGenerator().visit(tree)
    return PREAMBLE + code, RUNTIME_C
