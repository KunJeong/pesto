from collections import deque
dq = deque([-1, 10])
copied = deque(dq)
front = dq[0]
length = len(dq)
rot = deque(dq)
rot.rotate(1)
rot = deque(dq)
rot.rotate(1)

class Runner:

    def go(self):
        return deque().pop()
Runner().go()
