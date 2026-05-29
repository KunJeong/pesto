"""Mutate CPython core source file(s) and rebuild the interpreter."""

import json
import os
import re
import subprocess
import sys

from . import paths
from .mutator import CPYTHON_DEFINES, CPYTHON_INCLUDE_PATHS, mutate_file


def _mutate_targets(root, targets, mutations, meta_path):
    """Mutate each target in place; write unified metadata with global IDs."""
    all_mutations = []
    file_entries = []
    id_offset = 0
    runtime_written = False
    mutated_targets = {}

    for rel_file, func_list in targets.items():
        target = root / rel_file
        print(f"Mutating {rel_file} ...")
        try:
            mutated_code, runtime_code, mutation_count, mutation_meta = mutate_file(
                str(target),
                cpp_args=CPYTHON_DEFINES,
                include_paths=CPYTHON_INCLUDE_PATHS,
                enabled_mutations=mutations,
                target_functions=func_list,
                id_offset=id_offset,
            )
        except Exception as e:
            msg = str(e).splitlines()[0][:80]
            print(f"Failed [{type(e).__name__}] {msg}")
            return False
        print(f"Done: {mutation_count} mutations in {rel_file}")

        if mutation_count > 0:
            target.write_text(mutated_code)
            mutated_targets[rel_file] = func_list
            if not runtime_written:
                (target.parent / "pesto_runtime.c").write_text(runtime_code)
                runtime_written = True

        file_entries.append({
            "file": str(target),
            "mutation_count": mutation_count,
            "id_range": [id_offset, id_offset + mutation_count - 1] if mutation_count else [],
        })
        all_mutations.extend(mutation_meta)
        id_offset += mutation_count

    meta_path.write_text(json.dumps({
        "mutation_count": id_offset,
        "mutations": all_mutations,
        "files": file_entries,
    }, indent=2))
    return mutated_targets


def _patch_makefile(root, targets) -> None:
    first_target = root / next(iter(targets))
    runtime_rel = first_target.parent.relative_to(root)
    runtime_obj = f"{runtime_rel}/pesto_runtime.o"
    runtime_src = f"{runtime_rel}/pesto_runtime.c"

    makefile = root / "Makefile"
    content = makefile.read_text()
    additions = ""
    if "# PESTO additions" not in content:
        additions += (
            f"\n# PESTO additions\n"
            f"OBJECT_OBJS += {runtime_obj}\n\n"
            f"{runtime_obj}: {runtime_src}\n"
            f"\t$(CC) -c -O2 -o $@ $<\n"
        )

    mutated_objs = []
    for rel_file in targets:
        t = root / rel_file
        t_rel = t.parent.relative_to(root)
        mutated_obj = f"{t_rel}/{t.stem}.o"
        mutated_src = f"{t_rel}/{t.stem}.c"
        mutated_objs.append(mutated_obj)
        pesto_rule = (
            f"\n{mutated_obj}: {mutated_src}\n"
            f"\t$(CC) $(filter-out -O% -Werror=implicit-function-declaration -std=%,"
            f"$(PY_CORE_CFLAGS)) -std=gnu11 -O0 -DUSE_COMPUTED_GOTOS=0"
            f" -Wno-implicit-function-declaration"
            f" -Wno-incompatible-pointer-types"
            f" -Wno-int-conversion -c -o $@ $<\n"
        )
        if pesto_rule not in content:
            additions += pesto_rule

    all_objs = " ".join([runtime_obj] + mutated_objs)
    pesto_build_entry = (
        f"\n.PHONY: pesto-build\n"
        f"pesto-build: {all_objs}\n"
        f"\t$(AR) r $(BLDLIBRARY) {all_objs}\n"
        f"\t$(LINKCC) $(PY_CORE_LDFLAGS) $(LINKFORSHARED) -o $(BUILDPYTHON)"
        f" Programs/python.o $(LINK_PYTHON_OBJS) $(LIBS) $(MODLIBS) $(SYSLIBS)\n"
    )
    if pesto_build_entry not in content:
        if "pesto-build:" in content:
            content = re.sub(
                r"\n\.PHONY: pesto-build\npesto-build:.*?\n\t.*?\n\t.*?\n",
                "",
                content,
            )
            makefile.write_text(content)
        additions += pesto_build_entry
    if additions:
        makefile.write_text(content + additions)
        print("Patched Makefile.")


def build_mutated_cpython(file: str = "Objects/longobject.c", mutations=None, targets=None) -> bool:
    """Mutate CPython source file(s) and rebuild patched CPython.

    ``targets`` maps repo-relative paths to function lists (None = all functions
    in that file); when omitted, ``file`` is mutated in full. Returns True on
    success.
    """
    sys.setrecursionlimit(50000)

    root = paths.VENDOR_CPYTHON
    if not root.exists():
        sys.exit("Patched CPython not found. Run: scripts/build-patched-cpython.sh")

    if targets is None:
        targets = {file: None}

    meta_path = paths.LONGOBJECT_META
    if meta_path.exists():
        print("Already mutated, skipping mutation step.")
        mutated_targets = targets
    else:
        mutated_targets = _mutate_targets(root, targets, mutations, meta_path)
        if mutated_targets is False:
            return False

    _patch_makefile(root, mutated_targets)

    print("Building mutated CPython ...")
    result = subprocess.run(
        ["make", "-C", str(root), f"-j{os.cpu_count() or 4}", "pesto-build"],
    )
    if result.returncode == 0:
        print(f"\nBuild complete: {root}/python")
        return True
    print("\nBuild failed.")
    return False
