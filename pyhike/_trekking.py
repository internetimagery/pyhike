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

    def visit_directory(self, fullname, directorypath, traveler):
        # type: (str, str, TrailBlazer) -> Optional[bool]
        """ Visit a directory (outside or inside a package) """

    def visit_file(self, fullname, filepath, traveler):
        # type: (str, str, TrailBlazer) -> Optional[bool]
        """ Visit a python module filepath """

    def visit_module(self, fullname, module, traveler):
        # type: (str, types.ModuleType, TrailBlazer) -> Optional[bool]
        """ Visit a module """

    def visit_class(self, fullname, class_, traveler):
        # type: (str, type, TrailBlazer) -> Optional[bool]
        """ Visit a class """

    def visit_function(self, fullname, func, parent, traveler):
        # type: (str, Callable, Any, TrailBlazer) -> None
        """ Visit a function """

    def visit_method(self, fullname, func, class_, traveler):
        # type: (str, Callable, type, TrailBlazer) -> None
        """ Visit a method """

    def visit_classmethod(self, fullname, func, class_, traveler):
        # type: (str, Callable, type, TrailBlazer) -> None
        """ Visit a class method """

    def visit_staticmethod(self, fullname, func, class_, traveler):
        # type: (str, Callable, type, TrailBlazer) -> None
        """ Visit a static method """

    def visit_property(self, fullname, func, class_, traveler):
        # type: (str, Callable, type, TrailBlazer) -> None
        """ Visit a property """

    def visit_attribute(self, fullname, value, parent, traveler):
        # type: (str, Any, Any, TrailBlazer) -> None
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

    def roam_module(self, module, name=""):
        # type: (types.ModuleType, str) -> TrailBlazer
        """ Wander through a module """
        if not name:
            name = self._join(module.__package__ or "", module.__name__)
        self._enqueue(self._MODULE, self._walk_module, module, name)
        return self

    def roam_class(self, class_, fullname=""):
        # type: (type, str) -> TrailBlazer
        """ Travel into a class """
        if not fullname:
            fullname = self._name(class_)
        if fullname in sys.modules:
            # Issue when people dynamically add classes to sys.modules
            # trying to create namespaces. Happens in typing module.
            # They want us to treat this class like it was module? So we shall...
            self._enqueue(
                self._MODULE, self._walk_module, sys.modules[fullname], fullname
            )
        else:
            self._enqueue(self._CLASS, self._walk_class, class_, fullname)
        return self

    def _walk_directory(self, directory, package_name):
        # type: (str, str) -> None

        with self._scope(package_name):
            if self._visitor.visit_directory(package_name, directory, self):
                return

            modules = set(["__init__"])
            for name in os.listdir(directory):
                fullpath = os.path.join(directory, name)

                package_file = self._get_package(fullpath)
                if package_file:
                    self.roam_file(package_file, self._join(package_name, name))
                    self.roam_directory(fullpath, self._join(package_name, name))
                    modules.add(name)
                    continue

                match = MODULE_REG.match(name)
                if not match or match.group(1) in modules:
                    continue
                # Don't follow modules more than once. eg py+pyc
                modules.add(match.group(1))
                self.roam_file(fullpath, package_name)

    def _walk_file(self, filepath, package_name):
        # type: (str, str) -> None
        match = MODULE_REG.match(os.path.basename(filepath))
        if not match:
            raise ValueError(
                "File path provided is not a valid module {}".format(filepath)
            )
        module_name = match.group(1)
        if module_name == "__init__":
            if not package_name:
                fullname = os.path.basename(filepath)
            else:
                fullname = package_name
        else:
            fullname = self._join(package_name, module_name)

        with self._scope(fullname):
            if self._visitor.visit_file(fullname, filepath, self):
                return

            # Ensure module (and other imports within it) work
            if not package_name:
                package_path = os.path.dirname(filepath)
                if module_name == "__init__":
                    package_path = os.path.dirname(package_path)
                if package_path not in sys.path:
                    sys.path.insert(0, package_path)

            module = importlib.import_module(fullname)
            self.roam_module(module, fullname)

    def _walk_module(self, module, fullname):
        # type: (types.ModuleType, str) -> None
        with self._scope(fullname):
            if self._visitor.visit_module(fullname, module, self):
                return
            for name, value in inspect.getmembers(module):
                subname = self._join(fullname, name, True)
                if inspect.ismodule(value):
                    self.roam_module(value, subname)
                elif inspect.isclass(value):
                    self.roam_class(value, subname)
                elif inspect.isroutine(value):
                    self._enqueue(
                        self._FUNCTION, self._walk_function, value, module, subname
                    )
                else:
                    self._enqueue(
                        self._ATTRIBUTE, self._walk_attribute, value, module, subname
                    )

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
                if attr.kind == "data":
                    if inspect.isclass(attr.object):
                        self._enqueue(
                            self._CLASS, self._walk_class, attr.object, subname
                        )
                        continue
                    if inspect.isroutine(attr.object):
                        self._enqueue(
                            self._FUNCTION,
                            self._walk_function,
                            attr.object,
                            class_,
                            subname,
                        )
                        continue
                priority, func = self._class_kind_map[attr.kind]
                self._enqueue(priority, func, attr.object, class_, subname)

    def _walk_function(self, func, parent, fullname):
        # type: (Callable, Any, str) -> None
        with self._scope(fullname):
            self._visitor.visit_function(fullname, func, parent, self)

    def _walk_method(self, func, class_, fullname):
        # type: (Callable, type, str) -> None
        with self._scope(fullname):
            self._visitor.visit_method(fullname, func, class_, self)

    def _walk_classmethod(self, func, class_, fullname):
        # type: (Callable, type, str) -> None
        with self._scope(fullname):
            self._visitor.visit_classmethod(fullname, func, class_, self)

    def _walk_staticmethod(self, func, class_, fullname):
        # type: (Callable, type, str) -> None
        with self._scope(fullname):
            self._visitor.visit_staticmethod(fullname, func, class_, self)

    def _walk_property(self, func, class_, fullname):
        # type: (Callable, type, str) -> None
        with self._scope(fullname):
            self._visitor.visit_property(fullname, func, class_, self)

    def _walk_attribute(self, value, parent, fullname):
        # type: (Any, Any, str) -> None
        with self._scope(fullname):
            self._visitor.visit_attribute(fullname, value, parent, self)

    @staticmethod
    def _join(name1, name2, module=False):
        # type: (str, str, bool) -> str
        if not name1:
            return name2
        name = name1 + "." + name2
        if not module:
            return name
        # Check if we are diverging from all known modules,
        # then add a colon to indicate the break point.
        if name not in sys.modules and ":" not in name:
            name = name1 + ":" + name2
        return name

    def _name(self, object_):
        # type: (type) -> str
        try:
            name = object_.__qualname__
        except AttributeError:
            name = object.__name__
        return self._join(object_.__module__, name)

    @staticmethod
    def _get_package(path):
        # type: (str) -> Optional[str]
        if not os.path.isdir(path):
            return None
        for name in os.listdir(path):
            match = MODULE_REG.match(name)
            if not match:
                continue
            if match.group(1) == "__init__":
                return os.path.join(path, name)
        return None

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
            if sys.version_info.major != 2:
                # This cleanup step doesn't seem to be working in python2
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
