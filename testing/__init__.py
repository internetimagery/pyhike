import unittest

import os

from pyhike import TrailBlazer, Chart

TESTDIR = os.path.join(os.path.dirname(__file__), "testdata")


class TestVisitor(Chart):
    def __init__(self):
        self.errors = []
        self.files = {}
        self.modules = {}
        self.classes = {}

    def error(self, *err):
        self.errors.append(err)

    def visit_file(self, name, path, _):
        self.files[name] = path

    def visit_module(self, name, module, _):
        self.modules[name] = module.__name__

    def visit_class(self, name, class_, _):
        self.classes[name] = class_.__name__


class TestDirectory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_simple = os.path.join(TESTDIR, "test_simple.py")
        cls.test_error = os.path.join(TESTDIR, "test_error.py")

    def setUp(self):
        self.visitor = TestVisitor()
        self.traveler = TrailBlazer(self.visitor)

    def test_visit_directory(self):
        self.traveler.roam_directory(TESTDIR)
        self.assertEqual(
            self.visitor.files,
            {"test_simple": self.test_simple, "test_error": self.test_error,},
        )

    def test_visit_file(self):
        self.traveler.roam_file(self.test_simple)
        self.assertEqual(
            self.visitor.files, {"test_simple": self.test_simple},
        )

    def test_visit_module(self):
        self.traveler.roam_file(self.test_simple)
        self.assertEqual(
            self.visitor.modules, {"test_simple": "test_simple"},
        )

    def test_visit_module_error(self):
        self.traveler.roam_file(self.test_error)
        self.assertEqual(
            self.visitor.modules, {},
        )
        (error,) = self.visitor.errors
        self.assertEqual(RuntimeError, error[0])


if __name__ == "__main__":
    unittest.main()
