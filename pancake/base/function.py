"""Function 基类"""

from pancake.dough import Dough


class Function(Dough):
    """方法类 — 包装函数，提供 call() 方法

    使用时直接调用即可:
        my_func = MyFunction()
        result = my_func(args)
    """

    def call(self, *args, **kwargs):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)
