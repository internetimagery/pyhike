from typing import Iterator


import os
import re

MODULE_REG = re.compile(r"(\w+)\.(py[cwd]?|so)$")
MODULE_INIT = ("__init__", "__main__")


class Chart(object):
    """ Options to take while traversing objects """

    pass


class Trail(object):
    """
    Visit each object along the way!
    For each visitation, return True to prevent further descent on the path.
    """

    def enter(self, fullname):
        # type: (str) -> None
        """ Run before visiting anything """

    def leave(self, fullname):
        # type: (str) -> None
        """ Run after visiting """

    def visit_file(self, fullname, filepath, traveler):
        # type: (str, str, TrailBlazer) -> bool
        """ Visit a python module filepath """
        return False


class TrailBlazer(object):
    """ Carve a trail through python objects! """

    def __init__(self, options, visitor):
        # type: (Chart, Trail) -> None
        self._options = options
        self._visitor = visitor

    def roam_directory(self, filepath, fullname=""):
        # type: (str, str) -> None
        """
        Walk files in a directory. Only following
        python modules.
        """
        # Gather information first, as we don't want to
        # follow duplicate modules (eg .py and .pyc of the same name)
        modules = {}
        for name in os.listdir(filepath):
            fullpath = os.path.join(filepath, name)
            if os.path.isfile(fullpath):
                match = MODULE_REG.match(name)
                if not match:
                    continue
                if match.group(1) == "__init__":
                    module_name = os.path.basename(filepath)
                else:
                    module_name = match.group(1)
                modules[module_name] = fullpath
            elif os.path.isdir(fullpath):
                for subname in os.listdir(fullpath):
                    match = MODULE_REG.match(subname)
                    if not match or match.group(1) != "__init__`":
                        continue
                    modules[name] = os.path.join(fullpath, subname)
                    break
        for module_name, module_path in modules.items():
            sub_fullname = self._join(fullname, module_name)
            self._visitor.enter(sub_fullname)
            if not self._visitor.visit_file(sub_fullname, module_path, self):
                self.roam_file(module_path, sub_fullname)
            self._visitor.leave(sub_fullname)

    def roam_file(self, filepath, fullname=""):
        # type: (str, str)-> None
        """ Import a new module from filepath """
        pass

    def roam_module(self, module, fullname=""):
        # type: (object, str) -> None
        """ Wander through a module """
        pass

    def roam_class(self, class_, fullname=""):
        # type: (object, str) -> None
        """ Travel into a class """
        pass

    @staticmethod
    def _join(name1, name2):
        # type: (str, str) -> str
        if not name1:
            return name2
        return "{}.{}".format(name1, name2)
