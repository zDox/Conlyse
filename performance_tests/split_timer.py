import time

class SplitTimer:
    def __init__(self):
        self.start = time.perf_counter()
        self.last = self.start
        self.splits = {}
        self.call_counts = {}

    def split(self, label: str | None):
        now = time.perf_counter()
        if label is not None:
            self.splits[label] = self.splits.get(label, 0) + (now - self.last)
            self.call_counts[label] = self.call_counts.get(label, 0) + 1
        self.last = now

    def report(self):
        total = sum(t for _, t in self.splits.items())
        for label, t in self.splits.items():
            print(f"{label}: {t*1000:.2f} ms {t/total*100:.1f}% called {self.call_counts[label]} times")
