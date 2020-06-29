from typing import Iterator, Optional


import os
import re
import imp

MODULE_REG = re.compile(
    r"(\w+)({})$".format(
        "|".join(re.escape(suffix) for suffix, _, _ in imp.get_suffixes())
    )
)


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
                module_name = self._module_name(fullpath)
                if module_name:
                    modules[module_name] = fullpath
            elif os.path.isdir(fullpath):
                for subname in os.listdir(fullpath):
                    subpath = os.path.join(fullpath, subname)
                    module_name = self._module_name(subpath)
                    if not module_name or module_name != subname:
                        continue
                    modules[name] = subpath
                    break
        for name in sorted(modules):
            self.roam_file(modules[name], fullname)

    def roam_file(self, filepath, fullname=""):
        # type: (str, str) -> None
        """ Import a new module from filepath """
        module_name = self._module_name(filepath)
        if not module_name:
            raise ValueError(
                "File path provided is not a valid module {}".format(filepath)
            )
        subname = self._join(fullname, module_name)
        self._visitor.enter(subname)
        if not self._visitor.visit_file(subname, filepath, self):
            module_params = imp.find_module(subname, [os.path.dirname(filepath)])
            module = imp.load_module(subname, *module_params)
            self.roam_module(module, subname)
        self._visitor.leave(subname)

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

    @staticmethod
    def _module_name(filepath):
        # type: (str) -> Optional[str]
        match = MODULE_REG.match(os.path.basename(filepath))
        if not match:
            return None
        if match.group(1) == "__init__":
            directory = os.path.dirname(filepath)
            return os.path.basename(directory)
        return match.group(1)
