import math
value = 0
other = 3
flag = True
nums = [7, 10, 1]
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
    range('x')
finally:
    marker = 1
