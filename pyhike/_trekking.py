from typing import Iterator, Optional, Dict, Type


import os
import re
import sys
import imp
import types
import inspect
import contextlib

MODULE_REG = re.compile(
    r"(\w+)({})$".format(
        "|".join(re.escape(suffix) for suffix, _, _ in imp.get_suffixes())
    )
)


class Chart(object):
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

    def error(self, errType, errVal, errTrace):
        # type: (Type[Exception], Exception, types.TracebackType) -> Optional[bool]
        """ Respond to errors """

    def visit_file(self, fullname, filepath, traveler):
        # type: (str, str, TrailBlazer) -> Optional[bool]
        """ Visit a python module filepath """

    def visit_module(self, fullname, module, traveler):
        # type: (str, object, TrailBlazer) -> Optional[bool]
        """ Visit a module """

    def visit_class(self, fullname, class_, traveler):
        # type: (str, object, TrailBlazer) -> Optional[bool]
        """ Visit a class """


class TrailBlazer(object):
    """ Carve a trail through python objects! """

    def __init__(self, visitor):
        # type: (Chart) -> None
        self._visitor = visitor
        self._seen = {}  # type: Dict[int, object]

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
        with self._scope(subname):
            if self._visitor.visit_file(subname, filepath, self):
                return
            module_params = imp.find_module(subname, [os.path.dirname(filepath)])
            try:
                module = imp.load_module(subname, *module_params)
            except Exception:
                if self._visitor.error(*sys.exc_info()):
                    raise
            else:
                self.roam_module(module, subname)

    def roam_module(self, module, fullname):
        # type: (object, str) -> None
        """ Wander through a module """
        if id(module) in self._seen:
            return
        with self._scope(fullname):
            if self._visitor.visit_module(fullname, module, self):
                return
            for name, value in inspect.getmembers(module):
                subname = self._join(fullname, name)
                if inspect.isclass(value):
                    self.roam_class(value, subname)

    def roam_class(self, class_, fullname):
        # type: (object, str) -> None
        """ Travel into a class """
        with self._scope(fullname):
            if self._visitor.visit_class(fullname, class_, self):
                return
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

    @contextlib.contextmanager
    def _scope(self, fullname):
        self._visitor.enter(fullname)
        yield
        self._visitor.leave(fullname)
