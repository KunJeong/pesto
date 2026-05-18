from collections import deque
dq = deque([0, 0])
copied = deque(dq)
front = dq[0]
length = len(dq)
rot = deque(dq)
rot.rotate(1)
if dq:
    head = dq[0]
else:
    head = 0
if dq:
    head = dq[0]
else:
    head = 0

class Runner:

    def go(self):
        return deque().pop()
Runner().go()
