# An adventure through code

Pyhike is an interface for tools that wish to walk live objects for inspection.

Yep. Pretty simple!

> This is still wip, as it is being developed alongside another tool making use of it.

* [Installation](#installation)
* [Usage](#usage)
* [Notes](#notes)

## Installation

Install via pip. Python 2 and 3 compatible

```sh
python -m pip install -U pyhike
```

## Usage

There are two parts to the API.

* [Chart](#chart): Visitor interface that you will subclass and provide custom logic on top of
* [TrailBlazer](#trailblazer): Traversal class that will act on the visitor

```py
from pyhike import Chart, TrailBlazer

class MyVisitor(Chart):

    def visit_method(self, name, method, class_, trailblazer):
        print("A METHOD!", name, method)

TrailBlazer(MyVisitor()).roam_file("/path/to/somefile.py").hike()
# A METHOD somefile:SomeClass.some_method <some_method at 0x123123123>
```

Create a visitor (or multiple layers of subclass if it makes design sense) for functionality.

Create a traversal object, and add things to traverse (__roam_file__, __roam_class__, __roam_directory__, etc).

Trigger the traversal (__hike__).

### TrailBlazer

Contains the following methods to add things for traversal. They are all chainable. They can also be used during live traversal to dynamically search new locations (see the visitor methods below).

* __roam_directory__(filepath) : Walk directory looking for modules. This does not recurse into non-module directories.
* __roam_file__(filepath) : import and traverse a file, given the filepath
* __roam_module__(module) : search an already imported module object
* __roam_class__(class_) : search an already loaded class object

Finally the __hike__() method kicks off the traversal, and off we go. Adventure is out there!

### Chart

Subclass this for your own adventure! This object will have its methods called for each object
type visited along the way.

The methods all recieve an instance of the active traversal object so they can dynamically add more things to check if needed.

Returning _True_ from a method will stop further traversal along that path at that point (eg return true visiting a class will not traverse its methods).

* __visit_directory__(name, directorypath, traveler)
* __visit_file__(name, filepath, traveler)
* __visit_module__(name, module, traveler)
* __visit_class__(name, class_, traveler)
* __visit_function__(name, func, parent, traveler)
* __visit_method__(name, func, class_, traveler)
* __visit_classmethod__(name, func, class_, traveler)
* __visit_staticmethod__(name, func, class_, traveler)
* __visit_property__(name, func, class_, traveler)
* __visit_attribute__(name, value, parent, traveler)

There are a few special methods as well for consideration, that may make life a little easier.

* __enter__(name) Run before traversing into anything, with the name of the thing it's about to traverse into.
* __leave__(name) Run after finishing the traversal. Run with the same name as it was entered.
* __error__(errType, errVal, errTrace) Run anytime an error occurrs during traversal. Return _True_ to allow the error to propigate up halting traversal.

## Notes

__There is no attempt at resolving circular code traversal.__ This is left up to the user of the visitor to provide.
This is to provide more flexability on behalf of the visitor logic. Remember that visitor methods can halt further traversal by returning _True_.

The traversal happens mostly from the bottom up. It visits first come first serve on a priority basis.
So things are visited in this order:

* Directories
* Files
* Modules
* Classes
* Functions / Methods
* Attributes

The name provided to the visitor methods is generated from the path taken to reach the object.
eg *some_package.some_module:SomeClass.some_method*. This means that it does not reflect the name of the objects definition. But instead an import path that would lead you there.

The name splits modules and qualified names by colon.

Errors that occurr during traversal are suppressed, and forwarded to the __error__ visitation method. To allow them to propigate normally, and halt everything return _True_ in the __error__ method.

