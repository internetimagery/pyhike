from typing import Iterator, Optional, Dict, Type, Any, List, Tuple, Callable


import os
import re
import sys
import imp
import types
import heapq
import logging
import inspect
import importlib
import functools
import contextlib

LOG = logging.getLogger(__name__)

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
        # type: (str, types.ModuleType, TrailBlazer) -> Optional[bool]
        """ Visit a module """

    def visit_class(self, fullname, class_, traveler):
        # type: (str, object, TrailBlazer) -> Optional[bool]
        """ Visit a class """

    def visit_function(self, fullname, func, traveler):
        # type: (str, Callable, TrailBlazer) -> None
        """ Visit a function """

    def visit_method(self, fullname, func, traveler):
        # type: (str, Callable, TrailBlazer) -> None
        """ Visit a method """

    def visit_classmethod(self, fullname, func, traveler):
        # type: (str, Callable, TrailBlazer) -> None
        """ Visit a class method """

    def visit_staticmethod(self, fullname, func, traveler):
        # type: (str, Callable, TrailBlazer) -> None
        """ Visit a static method """

    def visit_property(self, fullname, func, traveler):
        # type: (str, Callable, TrailBlazer) -> None
        """ Visit a property """

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
        self._queue = []  # type: List[Tuple[int, int, Callable[[], None]]]
        self._tiebreaker = 0
        self._class_kind_map = {
            "data": (self._ATTRIBUTE, self._walk_attribute),
            "method": (self._FUNCTION, self._walk_method),
            "property": (self._FUNCTION, self._walk_property),
            "static method": (self._FUNCTION, self._walk_staticmethod),
            "class method": (self._FUNCTION, self._walk_classmethod),
        }

    def hike(self):
        """ Travel through the objects provided! """
        # Using a queue so we walk bottom up
        with self._cleanup():
            while self._queue:
                _, _, func = heapq.heappop(self._queue)
                func()

    def roam_directory(self, filepath, package_name=""):
        # type: (str, str) -> TrailBlazer
        """
        Walk files in a directory. Only following
        python modules.
        """
        self._enqueue(self._DIRECTORY, self._walk_directory, filepath, package_name)
        return self

    def roam_file(self, filepath, package_name=""):
        # type: (str, str) -> TrailBlazer
        """ Import a new module from filepath """
        self._enqueue(self._FILE, self._walk_file, filepath, package_name)
        return self

    def roam_module(self, module, module_name=""):
        # type: (types.ModuleType, str) -> TrailBlazer
        """ Wander through a module """
        if not module_name:
            module_name = self._join(module.__package__ or "", module.__name__)
        self._enqueue(self._MODULE, self._walk_module, module, module_name)
        return self

    def roam_class(self, class_, fullname=""):
        # type: (type, str) -> TrailBlazer
        """ Travel into a class """
        if not fullname:
            fullname = self._name(class_)
        self._enqueue(self._CLASS, self._walk_class, class_, fullname)
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

    def _walk_file(self, filepath, package_name):
        # type: (str, str) -> None
        module_name = self._module_name(filepath)
        if not module_name:
            raise ValueError(
                "File path provided is not a valid module {}".format(filepath)
            )
        subname = self._join(package_name, module_name)

        with self._scope(subname):
            if self._visitor.visit_file(subname, filepath, self):
                return

            # Ensure module (and other imports within it) work
            if not package_name:
                package_path = os.path.dirname(filepath)
                if package_path not in sys.path:
                    sys.path.insert(0, package_path)

            module = importlib.import_module(subname)
            self.roam_module(module, subname)

    def _walk_module(self, module, fullname):
        # type: (types.ModuleType, str) -> None
        with self._scope(fullname):
            if self._visitor.visit_module(fullname, module, self):
                return
            for name, value in inspect.getmembers(module):
                subname = self._join(fullname, name)
                if inspect.ismodule(value):
                    self.roam_module(value, subname)
                elif inspect.isclass(value):
                    self.roam_class(value, subname)
                elif inspect.isroutine(value):
                    self._enqueue(self._FUNCTION, self._walk_function, value, subname)
                else:
                    self._enqueue(self._ATTRIBUTE, self._walk_attribute, value, subname)

    def _walk_class(self, class_, fullname):
        # type: (type, str) -> None
        with self._scope(fullname):
            if self._visitor.visit_class(fullname, class_, self):
                return
            if class_ is type:
                # Recursion safeguards are expected to be provided by the visitor
                # however this safeguard is hard coded.
                return
            for attr in inspect.classify_class_attrs(class_):
                subname = self._join(fullname, attr.name)
                priority, func = self._class_kind_map[attr.kind]
                self._enqueue(priority, func, attr.object, subname)

    def _walk_function(self, func, fullname):
        # type: (Callable, str) -> None
        with self._scope(fullname):
            self._visitor.visit_function(fullname, func, self)

    def _walk_method(self, func, fullname):
        # type: (Callable, str) -> None
        with self._scope(fullname):
            self._visitor.visit_method(fullname, func, self)

    def _walk_classmethod(self, func, fullname):
        # type: (Callable, str) -> None
        with self._scope(fullname):
            self._visitor.visit_classmethod(fullname, func, self)

    def _walk_staticmethod(self, func, fullname):
        # type: (Callable, str) -> None
        with self._scope(fullname):
            self._visitor.visit_staticmethod(fullname, func, self)

    def _walk_property(self, func, fullname):
        # type: (Callable, str) -> None
        with self._scope(fullname):
            self._visitor.visit_property(fullname, func, self)

    def _walk_attribute(self, value, fullname):
        # type: (Any, str) -> None
        with self._scope(fullname):
            self._visitor.visit_attribute(fullname, value, self)

    @staticmethod
    def _join(name1, name2):
        # type: (str, str) -> str
        if not name1:
            return name2
        return "{}.{}".format(name1, name2)

    def _name(self, object_):
        # type: (type) -> str
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

    def _enqueue(self, priority, func, *args):
        # type: (int, Callable, *Any) -> None
        self._tiebreaker += 1
        heapq.heappush(
            self._queue, (priority, self._tiebreaker, lambda: func(*args),),
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
            LOG.exception("Error while traversing %s", fullname)
        finally:
            self._visitor.leave(fullname)

    @contextlib.contextmanager
    def _cleanup(self):
        """ * Disable bytecode generation, so our imports
            dont leave traces all over code bases
            * Restore sys.modules so our imports don't mess with
            code any more than is unavoidable.
        """
        bytecode = sys.dont_write_bytecode
        modules = sys.modules.copy()
        path = sys.path[:]
        sys.dont_write_bytecode = True
        try:
            yield
        finally:
            sys.dont_write_bytecode = bytecode
            sys.modules = modules
            sys.path = path

    # Have to chuck this at the bottom, so functions are defined
    _CLASS_ATTR_MAP = {
        "data": (_ATTRIBUTE, _walk_attribute),
        "method": (_FUNCTION, _walk_function),
        "property": (_FUNCTION, _walk_function),
        "static method": (_FUNCTION, _walk_function),
        "class method": (_FUNCTION, _walk_function),
    }
