import time

class SplitTimer:
    def __init__(self):
        self.start = time.perf_counter()
        self.last = self.start
        self.splits = {}

    def split(self, label: str):
        now = time.perf_counter()
        self.splits[label] = self.splits.get(label, 0) + (now - self.last)
        self.last = now

    def report(self):
        total = sum(t for _, t in self.splits.items())
        for label, t in self.splits.items():
            print(f"{label}: {t*1000:.2f} ms {t/total*100:.1f}%")
