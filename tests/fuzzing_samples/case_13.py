from pathlib import Path
p = Path('alpha/beta.txt')
child = p.with_suffix('.log')
parts = list(p.parts)
path_text = str(child)
parent = p.parent
parent_text = str(parent)
part_count = len(parts)
joined = p.joinpath('gamma')
joined_text = str(joined)
thunk = lambda: p.relative_to('zzz')
thunk()
