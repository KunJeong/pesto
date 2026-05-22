from collections import deque
dq = deque([-3, 3])
copied = deque(dq)
front = dq[0]
length = len(dq)
dq.append(7)
after = len(dq)
rot = deque(dq)
rot.rotate(1)
next(dq)
