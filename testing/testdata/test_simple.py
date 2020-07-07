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

    class test_method_descriptor(object):
        def __get__(self, obj, type_=None):
            pass

    test_method_descriptor = test_method_descriptor()

    class test_data_descriptor(object):
        def __get__(self, obj, type_=None):
            pass

        def __set__(self, obj, value):
            pass

    test_data_descriptor = test_data_descriptor()


def test_function(self):
    pass


test_attribute = 123
