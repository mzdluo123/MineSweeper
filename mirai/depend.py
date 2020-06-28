class Depend:
    def __init__(self, func, middlewares=[], cache=True):
        self.func = func
        self.middlewares = middlewares
        self.cache = cache