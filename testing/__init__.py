import unittest

import os
import logging

logging.basicConfig()

from pyhike import TrailBlazer, Chart

TESTDIR = os.path.join(os.path.dirname(__file__), "testdata")


class TestVisitor(Chart):
    def __init__(self):
        self.errors = []
        self.directories = {}
        self.files = {}
        self.modules = {}
        self.classes = {}
        self.functions = {}
        self.methods = {}
        self.classmethods = {}
        self.staticmethods = {}
        self.methoddescriptors = {}
        self.datadescriptors = {}
        self.properties = {}
        self.method_descriptors = {}
        self.attributes = {}

    def error(self, *err):
        self.errors.append(err)

    def visit_directory(self, name, path, _):
        self.directories[name] = path

    def visit_file(self, name, path, _):
        self.files[name] = path

    def visit_module(self, name, module, _):
        self.modules[name] = module.__name__

    def visit_class(self, name, class_, _):
        self.classes[name] = class_.__name__

    def visit_function(self, name, func, _, __):
        self.functions[name] = func.__name__

    def visit_method(self, name, func, _, __):
        self.methods[name] = func.__name__

    def visit_classmethod(self, name, func, _, __):
        self.classmethods[name] = func.__func__.__name__

    def visit_staticmethod(self, name, func, _, __):
        self.staticmethods[name] = func.__func__.__name__

    def visit_method_descriptor(self, name, desc, _, __):
        self.methoddescriptors[name] = desc.__get__.__name__

    def visit_data_descriptor(self, name, desc, _, __):
        self.datadescriptors[name] = desc.__get__.__name__

    def visit_property(self, name, func, _, __):
        self.properties[name] = func.fget.__name__

    def visit_attribute(self, name, value, _, __):
        self.attributes[name] = value


class TestTrailBlazer(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.test_simple = os.path.join(TESTDIR, "test_simple.py")
        cls.test_import_a = os.path.join(TESTDIR, "test_import_a.py")
        cls.test_import_b = os.path.join(TESTDIR, "test_import_b.py")
        cls.test_error = os.path.join(TESTDIR, "test_error.py")
        cls.test_package = os.path.join(TESTDIR, "test_package", "__init__.py")
        cls.test_submodule = os.path.join(TESTDIR, "test_package", "test_submodule.py")

    def setUp(self):
        self.visitor = TestVisitor()
        self.traveler = TrailBlazer(self.visitor)

    def test_visit_directory(self):
        self.traveler.roam_directory(TESTDIR).hike()
        self.assertEqual(
            self.visitor.files,
            {
                "test_simple": self.test_simple,
                "test_error": self.test_error,
                "test_import_a": self.test_import_a,
                "test_import_b": self.test_import_b,
                "test_package": self.test_package,
                "test_package.test_submodule": self.test_submodule,
            },
        )
        self.assertEqual(
            self.visitor.directories,
            {"": TESTDIR, "test_package": os.path.join(TESTDIR, "test_package")},
        )

    def test_visit_file(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            self.visitor.files, {"test_simple": self.test_simple},
        )

    def test_visit_module(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            self.visitor.modules,
            {
                "test_simple": "test_simple",
                "test_simple:test_import_a": "test_import_a",
                "test_simple:test_import_a.test_import_b": "test_import_b",
            },
        )

    def test_visit_module_error(self):
        self.traveler.roam_file(self.test_error).hike()
        self.assertEqual(
            self.visitor.modules, {},
        )
        (error,) = self.visitor.errors
        self.assertEqual(RuntimeError, error[1])

    def test_visit_class(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual("TestClass", self.visitor.classes["test_simple:TestClass"])

    def test_visit_function(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "test_function", self.visitor.functions["test_simple:test_function"]
        )

    def test_visit_method(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "test_method", self.visitor.methods["test_simple:TestClass.test_method"]
        )

    def test_visit_classmethod(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "test_classmethod",
            self.visitor.classmethods["test_simple:TestClass.test_classmethod"],
        )

    def test_visit_staticmethod(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "test_staticmethod",
            self.visitor.staticmethods["test_simple:TestClass.test_staticmethod"],
        )

    def test_visit_method_descriptor(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "__get__",
            self.visitor.methoddescriptors[
                "test_simple:TestClass.test_method_descriptor"
            ],
        )

    def test_visit_data_descriptor(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "__get__",
            self.visitor.datadescriptors["test_simple:TestClass.test_data_descriptor"],
        )

    def test_visit_property(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(
            "test_property",
            self.visitor.properties["test_simple:TestClass.test_property"],
        )

    def test_visit_attributes(self):
        self.traveler.roam_file(self.test_simple).hike()
        self.assertEqual(123, self.visitor.attributes["test_simple:test_attribute"])

    def test_propigate_visitor_fails(self):
        class ErrorVisitor(Chart):
            def __init__(self):
                self.error_count = 0

            def error(self, *_):
                self.error_count += 1

            def visit_class(self, *_):
                raise RuntimeError("Oh damn!")

        visitor = ErrorVisitor()
        traveler = TrailBlazer(visitor)
        traveler.roam_file(self.test_simple)
        with self.assertRaises(RuntimeError):
            traveler.hike()


if __name__ == "__main__":
    unittest.main()
