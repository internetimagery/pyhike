import test_import_a


class TestClass(object):
    __slots__ = ()

    def test_method(self):
        pass

    @classmethod
    def test_classmethod(cls):
        pass

    @staticmethod
    def test_staticmethod():
        pass

    @property
    def test_property(self):
        pass


def test_function(self):
    pass


test_attribute = 123
