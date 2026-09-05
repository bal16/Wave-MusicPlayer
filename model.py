class CounterModel:
    def __init__(self):
        self.counter = 0

    def add(self):
        self.counter += 1
        return self.counter

    def reset(self):
        self.counter = 0
        return self.counter
