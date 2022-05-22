from collections import deque

q= deque(maxlen=2)
q.append(None)
q.append(None)
if not any(q):
    print('yes')
else:
    print('No')