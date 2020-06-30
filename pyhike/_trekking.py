from typing import Iterator, Optional, Dict, Type, Any


import os
import re
import sys
import imp
import types
import heapq
import inspect
import functools
import contextlib

MODULE_REG = re.compile(
    r"(\w+)({})$".format(
        "|".join(re.escape(suffix) for suffix, _, _ in imp.get_suffixes())
    )
)


class Chart(object):
    """
    Lets adventure! Visit each object along the way!
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

    def visit_function(self, fullname, func, traveler):
        # type: (str, object, TrailBlazer) -> None
        """ Visit a function """

    def visit_attribute(self, fullname, value, traveler):
        # type: (str, Any, TrailBlazer) -> None
        """ Visit an attribute """


class TrailBlazer(object):
    """ Carve a trail through python objects! """

    # Visitation priority
    _DIRECTORY = 0
    _FILE = 1
    _MODULE = 2
    _CLASS = 3
    _FUNCTION = 4
    _ATTRIBUTE = 5

    def __init__(self, visitor):
        # type: (Chart) -> None
        self._visitor = visitor
        self._pass_error = False
        self._queue = []  # type: List[Tuple[int, int, object]]
        self._tiebreaker = 0

    def hike(self):
        """ Travel through the objects provided! """
        # Using a queue so we walk bottom up
        while self._queue:
            _, _, func = heapq.heappop(self._queue)
            func()

    def roam_directory(self, filepath, package_name=""):
        # type: (str, str) -> TraiBlazer
        """
        Walk files in a directory. Only following
        python modules.
        """
        self._enqueue(self._DIRECTORY, filepath, self._walk_directory, package_name)
        return self

    def roam_file(self, filepath, package_name=""):
        # type: (str, str) -> TrailBlazer
        """ Import a new module from filepath """
        self._enqueue(self._FILE, filepath, self._walk_file, package_name)
        return self

    def roam_module(self, module, module_name=""):
        # type: (object, str) -> TrailBlazer
        """ Wander through a module """
        if not module_name:
            module_name = self._join(module.__package__, module.__name__)
        self._enqueue(self._MODULE, module, self._walk_module, module_name)
        return self

    def roam_class(self, class_, fullname=""):
        # type: (object, str) -> TrailBlazer
        """ Travel into a class """
        if not fullname:
            fullname = self._name(class_)
        self._enqueue(self._CLASS, class_, self._walk_class, fullname)
        return self

    def _walk_directory(self, filepath, package_name=""):
        # type: (str, str) -> None

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
                    if not module_name or module_name != name:
                        continue
                    modules[name] = subpath
                    # Recurse into submodule
                    self.roam_directory(fullpath, self._join(package_name, module_name))
                    break
        for name in sorted(modules):
            self.roam_file(modules[name], package_name)

    def _walk_file(self, filepath, fullname=""):
        # type: (str, str) -> None
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
            module = imp.load_module(subname, *module_params)
            self.roam_module(module, subname)

    def _walk_module(self, module, fullname):
        # type: (object, str) -> None
        with self._scope(fullname):
            if self._visitor.visit_module(fullname, module, self):
                return
            self._walk_object(module, fullname)

    def _walk_class(self, class_, fullname):
        # type: (object, str) -> None
        with self._scope(fullname):
            if self._visitor.visit_class(fullname, class_, self):
                return
            if class_ is not type:
                self._walk_object(class_, fullname)

    def _walk_function(self, func, fullname):
        # type: (object, str) -> None
        with self._scope(fullname):
            self._visitor.visit_function(fullname, func, self)

    def _walk_attribute(self, value, fullname):
        # type: (Any, str) -> None
        with self._scope(fullname):
            self._visitor.visit_attribute(fullname, value, self)

    def _walk_object(self, object_, fullname):
        # type: (object, str) -> None
        for name, value in inspect.getmembers(object_):
            subname = self._join(fullname, name)
            if inspect.ismodule(value):
                self.roam_module(value, subname)
            elif inspect.isclass(value):
                self.roam_class(value, subname)
            elif inspect.isfunction(value):
                self._enqueue(self._FUNCTION, value, self._walk_function, subname)
            else:
                self._enqueue(self._ATTRIBUTE, value, self._walk_attribute, subname)

    @staticmethod
    def _join(name1, name2):
        # type: (str, str) -> str
        if not name1:
            return name2
        return "{}.{}".format(name1, name2)

    def _name(self, object_):
        # type: (object) -> str
        try:
            name = object_.__qualname__
        except AttributeError:
            name = object.__name__
        return self._join(object_.__module__, name)

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

    def _enqueue(self, priority, value, func, name):
        # type: (int, object, object, str) -> None
        self._tiebreaker += 1
        heapq.heappush(
            self._queue, (priority, self._tiebreaker, lambda: func(value, name),),
        )

    @contextlib.contextmanager
    def _scope(self, fullname):
        self._visitor.enter(fullname)
        try:
            yield
        except Exception:
            if self._pass_error:
                raise
            if self._visitor.error(*sys.exc_info()):
                self._pass_error = True
                raise
        finally:
            self._visitor.leave(fullname)
