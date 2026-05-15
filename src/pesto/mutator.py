import re
from copy import deepcopy

import pycparser
import pycparser.c_ast as c_ast
from pycparser import c_generator

BINARY_MUTATIONS = {
    "+":  ["<<", ">>"],
    "-":  ["<<", ">>"],
    "*":  ["<<", ">>"],
    "/":  ["<<", ">>"],
    "<":  ["<=", ">", ">=", "==", "!="],
    "<=": ["<",  ">", ">=", "==", "!="],
    ">":  ["<", "<=", ">=", "==", "!="],
    ">=": ["<", "<=", ">",  "==", "!="],
    "==": ["<", "<=", ">",  ">=", "!="],
    "!=": ["<", "<=", ">",  ">=", "=="],
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

PREAMBLE = "extern int __pesto_mutant_id;\n\n"

RUNTIME_C = """\
#include <stdio.h>

int __pesto_mutant_id = -1;

__attribute__((constructor))
static void pesto_init(void) {
    scanf("%d", &__pesto_mutant_id);
}
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

    def visit_BinaryOp(self, node):
        self.generic_visit(node)

        alternatives = BINARY_MUTATIONS.get(node.op)
        if not alternatives:
            return node

        result = node
        for alt_op in alternatives:
            mid = self._next_id()
            mutated = c_ast.BinaryOp(
                op=alt_op,
                left=deepcopy(node.left),
                right=deepcopy(node.right),
            )
            result = c_ast.TernaryOp(cond=_id_check(mid), iftrue=mutated, iffalse=result)
        return result

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
