import math
value = 2
other = 7
flag = True
nums = [0, 0, 7]
roots = [math.sqrt(x) for x in nums]
root_count = len(roots)
total = 0
for x in nums:
    total = total + x
if value < other:
    chosen = value
else:
    chosen = other
try:
    value < 1j
finally:
    marker = 1
