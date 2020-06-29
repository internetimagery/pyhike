import unittest

import os

from pyhike import TrailBlazer, Trail, Chart

TESTDIR = os.path.join(os.path.dirname(__file__), "testdata")

class TestVisitor(Trail):
    def __init__(self):
        self.files = {}
    
    def visit_file(self, name, path, _):
        self.files[name] = path


class TestDirectory(unittest.TestCase):

    def test_visit_directory(self):
       visitor = TestVisitor()
       TrailBlazer(Chart(), visitor).roam_directory(TESTDIR)
       self.assertEqual(visitor.files, {"test1": os.path.join(TESTDIR, "test1.py")}) 


if __name__ == "__main__":
    unittest.main()