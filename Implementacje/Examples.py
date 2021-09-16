import numpy as np


class ExampleFunction:
    def __init__(self, f__a, f__b, f__r, f__rho):
        self.f__a = f__a
        self.f__b = f__b
        self.f__r = f__r
        self.f__rho = f__rho

    def fun(self, x):
        pass


class Example1(ExampleFunction):
    def __init__(self):
        super().__init__(
            f__a=0,
            f__b=2 * np.pi + 0.5,
            f__r=3,
            f__rho=10e-4)

    def fun(self, x):
        def raw_f(xx):
            if 0 <= xx < np.pi:
                return np.sin(xx - np.pi)
            if np.pi <= xx <= 2 * np.pi + 0.5:
                return np.sin(xx - np.pi - 0.5)

        if isinstance(x, (list, np.ndarray)):
            return [raw_f(elem) for elem in x]
        elif isinstance(x, (float, np.float64)):
            return raw_f(x)
        raise Exception("x has to be list or float")


class Example2(ExampleFunction):
    def __init__(self):
        super().__init__(
            f__a=0,
            f__b=3 * np.pi,
            f__r=3,
            f__rho=10e-4)

    def fun(self, x):
        def raw_f(xx):
            if 0 <= xx < np.pi:
                return np.sin(xx)
            if np.pi <= xx <= 3 * np.pi:
                return np.sin(xx - np.pi)

        if isinstance(x, (list, np.ndarray)):
            return [raw_f(elem) for elem in x]
        elif isinstance(x, (float, np.float64)):
            return raw_f(x)
        raise Exception("x has to be list or float")