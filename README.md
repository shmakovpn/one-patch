# one-patch

![Tests](https://github.com/shmakovpn/one-patch/actions/workflows/python-package.yml/badge.svg)
[![codecov](https://codecov.io/github/shmakovpn/one-patch/graph/badge.svg?token=744XXMAKOZ)](https://codecov.io/github/shmakovpn/one-patch)
![Mypy](https://github.com/shmakovpn/one-patch/actions/workflows/python-package.yml/badge.svg)
[![pypi](https://img.shields.io/pypi/v/one-patch.svg)](https://pypi.python.org/pypi/one-patch)
[![downloads](https://static.pepy.tech/badge/one-patch/month)](https://pepy.tech/project/one-patch)
[![versions](https://img.shields.io/pypi/pyversions/one-patch.svg)](https://github.com/shmakovpn/one-patch)

Unit-test writing revolution!!

The `one-patch` way is:

 - One unit test for one function or method.
 - One patch for one unit test.

Or simply:
 - **One test - OnePatch**.

# Installation

```bash
pip install one-patch
```

# The problem

Let's try to write unit-test for something like this:

```python
# one_patch/testing_fixtures.py

def failed_function(x):
    raise RuntimeError(f'failed_one: {x}')


class FirstClass:
    first_class_const = '_first_class_const'

    def failed_method(self, x, y):
        raise RuntimeError('_failed_method')

    @classmethod
    def failed_class_method(cls, x, y):
        raise RuntimeError('_failed_class_method')

    @staticmethod
    def failed_static_method(x, y):
        raise RuntimeError('_failed_static_method')

    def success_method(self, method_argument):
        id_ = id(method_argument)

        self.failed_method(1, 2)
        self.failed_class_method(1, 2)
        self.failed_static_method(1, 2)
        return failed_function(id_)
```

```python
# pytest__my_code.py
import one_patch.testing_fixtures as tm  # tm means `testing module`
from unittest.mock import patch, MagicMock


class TestFirstClass:
    def test_success_method(self):
        """ Minimal test (without asserts) """
        with patch.object(tm, 'id', create=True) as _mock_id:  # 1
            with patch.object(tm.FirstClass, 'failed_method') as _mock_failed_method:  # 2
                with patch.object(tm.FirstClass, 'failed_class_method') as _mock_failed_class_method:  # 3
                    with patch.object(tm.FirstClass, 'failed_static_method') as _mock_failed_static_method:  # 4
                        with patch.object(tm, 'failed_function') as _mock_failed_function:  # 5
                            with patch.object(tm.FirstClass, '__init__', return_value=None):  # 6
                                fc = tm.FirstClass()
                                mock_method_argument = MagicMock()  # 7
                                _result = fc.success_method(method_argument=mock_method_argument)
```

`FirstClass.success_method` does not have errors itself, but it calls other functions and methods that will fail.
Thus, we need to mock them all.

Generally, testing methods or functions call others those need database access, redis, etc.
Those calls have to be mocked.

You can do not mock something, but then you will test not only target method or function.
You will test target method or function and all not mocked dependencies!!
If there are many not mocked dependencies, your test will very complex, very hard to read and difficulty to support.

In other hand we want only 1 failed test for 1 failed method. So, all dependencies have to be mocked.

How you can see in example below, writing a minimal test with mocking all dependencies is very expensive.
In the case below we need to write seven mocks to create a minimal test, that just performs successfully, but does not make any asserts.

Let us do something. Let us write a new in `reverse style`.

```python
# pytest__my_code__reverse.py
import one_patch.testing_fixtures as tm  # tm means `testing module`
from unittest.mock import patch, MagicMock


class TestFirstClass:
    def test_success_method(self):
        """ Minimal test (without asserts) """
        c = tm.FirstClass.success_method  # 'c' means pure callable to run, extracted from testing object
        mock_self = MagicMock()  # 1
        with patch.object(tm, 'id', create=True) as _mock_id:  # 2
            with patch.object(tm, 'failed_function') as _mock_failed_function:  # 3
                mock_method_argument = MagicMock()  # 4
                _result = c(self=mock_self, method_argument=mock_method_argument)
```

`Reverse` way is better. One need to create four mocks, but it is expensive too.

## The solution

Please. Look at the code of reverse test. If you write more unit-tests in reverse style, you will check out,
that all test are very similar to each other.

What happens if we mock all `scope` of testing method automatically in one statement?

```python
# pytest__my_code__one_patch.py
import one_patch.testing_fixtures as tm  # tm means `testing module`
from one_patch import OnePatch, OnePatchDTO


class TestFirstClass:
    def test_success_method(self):
        with OnePatch(func=tm.FirstClass.success_method) as op:  # 1! One test - OnePatch!
            op: OnePatchDTO
            _result = op.c(*op.args)
```

Miracle!!

All minimal tests needs only one mock!!

## Full one_patch_test

Let us add testing logic.

```python
# pytest__my_code__one_patch.py
import one_patch.testing_fixtures as tm  # tm means `testing module`
from one_patch import OnePatch, m  # 'm' is a shortcut for `typing.cast(Mock, something)`


class TestFirstClass:
    def test_success_method(self):
        """ 
        full test (100% coverage), 
        look pytest__one_patch.TestOnePatch.test_success_method for more information.
        Run this test in debugger, play around.
        """
        with OnePatch(func=tm.FirstClass.success_method) as op:  # 1 op contains all needed mocks
            # op.c - pure callable to run, extracted from testing object (method, function, descriptor and so on)
            assert op.c(*op.args) == m(tm.failed_function).return_value  # assert 1
            m(tm.failed_function).assert_called_once_with(m(tm).id.return_value)  # assert 2
            m(tm).id.assert_called_once_with(op.args.method_argument)  # assert 3
            # op.args, generated mock argument for op.c (pure callable to run)
            op.args.self.failed_method.assert_called_once_with(1, 2)  # assert 4
            # op.args.self is the same as op.args[0]
            op.args[0].failed_class_method.assert_called_once_with(1, 2)  # assert 5
            op.args[0].failed_static_method.assert_called_once_with(1, 2)  # assert 6
```

Testing method contains five not empty lines and six simple statements, look

```python
def failed_function(x):
    raise RuntimeError(f'failed_one: {x}')

def success_method(self, method_argument):
    id_ = id(method_argument)  # statement 1

    self.failed_method(1, 2)  # statement 2
    self.failed_class_method(1, 2)  # statement 3
    self.failed_static_method(1, 2)  # statement 4
    # return failed_function(id_)  # there two statements for unit test, see below
    result = failed_function(id_)  # # statement 5
    return result  # statement 6
```

Great: 6 asserts for 6 statements!!

Just imagine, that you did not write testing method from scratch. Then only one line was added, e.g. `my_other_func()`.
Previously one need to write four or seven mocks, plus mock for `my_other_func`, 
plus one or two asserts that checks: return value of `my_other_func`, and something like `assert_called_once_with`.

The price is so hi, that one do not write them at all.

```python
from one_patch import OnePatch, m  # 'm' is a shortcut for `typing.cast(Mock, something)`
import one_patch.testing_fixtures as tm  # tm means `testing module`

class TestFirstClass:
    def test_success_method(self):
        with OnePatch(func=tm.FirstClass.success_method) as op:
            assert op.c(*op.args) == m(tm.failed_function).return_value
            m(tm).my_other_func.assert_called_once_with()
```

The entry threshold has been drastically lowered. Such tests are much more likely to be written.


## Testing `@propery`

Use `fget` attribute of the property instead of the property itself.

```python
# example
class FirstClass:
    @property
    def some_property(self):
        return 'hello'
```

```python
from one_patch import OnePatch
import one_patch.testing_fixtures as tm  # tm means `testing module`


# Example test for @property
class TestFirstClass:
    def test_some_property(self):
        with OnePatch(tm.FirstClass.some_property.fget) as op:  # ! Use fget 
            assert op.c(*op.args) == 'hello'
```

## Testing logger message interpolation

```python
import logging
logger = logging.getLogger('some.logger')
logger.setLevel(logging.DEBUG)  # if level lower than DEBUG, debug message will not be interpolated


def do_log_debug_fail():
    """
    Calls logger with wrong message template
    """
    # TypeError: not all arguments converted during string formatting
    logger.debug('debug %s', 'fail', 1)
```

We want to test debug message matches other arguments passed to its call.

```python
from one_patch import OnePatch, PatchLogger
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_do_log_debug_success():
    with OnePatch(tm.do_log_debug_success, exclude_set={'logging', 'logger'}) as op:
        with PatchLogger(tm.logger):
            assert op.c(*op.args) is None
```

## Unpacking OnePatchDTO

`OnePatchDTO` supports unpacking. This can be useful to make your tests more compact.

```py
from one_patch import OnePatch
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_op_dto_unpack():
    with OnePatch(tm.FirstClass.success_method) as (op, c, args, s):
        assert op.c == c  # 'c' pure callable to run, extracted from testing object (method, function, descriptor and so one
        assert op.args == args  # mock arguments, generated for pure callable
        assert op.args.self == s  # 's' - self argument for testing method

    with OnePatch(tm.FirstClass.success_class_method) as (op, c, args, cls):
        assert op.c == c
        assert op.args == args
        assert op.args.cls == cls  # cls argument for testing class method

    with OnePatch(tm.FirstClass.success_static_method) as (op, c, args, s):
        assert op.c == c
        assert op.args == args
        assert s is None  # in case of staticmethod or function, where are no `self` or `cls` argument, `s` will be None
    
    # check short form
    with OnePatch(tm.FirstClass.success_static_method) as (op, c, *_):
        assert op.c == c

    with OnePatch(tm.FirstClass.success_method) as (op, *_, s):
        assert op.args.self == s
```

## Including (`include_set`) and excluding (`exclude_set`)

Sometimes we want to patch some builtins, like `id`, `open`, `type`, etc.
This is available using `include_set`.

```py
from one_patch import OnePatch, m  # 'm' is a shortcut for `typing.cast(Mock, something)`
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_success_static_method__include():
    with OnePatch(tm.FirstClass.success_static_method__include, include_set={'type'}) as op:
        r = op.c(*op.args)
        assert r == m(m(tm).type).return_value
```
`id` function is in `include_set` by default.

Note: `exclude_set` has more priority than `include_set`. So, if you put `id` in `exclude_set`, it will not be patched.
Example:

```py
from one_patch import OnePatch
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_success_static_method__exclude():
    with OnePatch(tm.FirstClass.success_static_method__exclude, exclude_set={'id'}) as op:
        r = op.c(*op.args)
        assert isinstance(r, int)  # id was not patched
```

Note: python3.10 cannot mock that already mocked. OnePatch will exclude mock objects from patching.
It is not possible to patch them using `include_set` or any other way.

In `exclude_set` you can use object itself or its python path. 
The excluded object will be collected in ReversePathDTO in `exclusions` dictionary.
Also, you can access it using both ways, the object itself or its python path.

```py
from one_patch import OnePatch
import one_patch.testing_fixtures as tm  # tm means `testing module`

# region exclude_set
with OnePatch(tm.InitCase.use_attrs_inited_in__init, exclude_set={tm.InitCase.__init__}) as op:
    # if you exclude a callable object, you can use this object to access it in op.exclusions.
    # Also, you can use the callable object in `exclude_set`
    op.exclusions[tm.InitCase.__init__].c(*op.exclusions[tm.InitCase.__init__].args)
    # op.exclusions[tm.InitCase.__init__] is the same as op.exclusions['InitCase.__init__']
    assert op.exclusions[tm.InitCase.__init__] is op.exclusions['InitCase.__init__']
    op.c(*op.args)

with OnePatch(tm.InitCase.use_attrs_inited_in__init, exclude_set={'InitCase.__init__'}) as op:
    op.exclusions[tm.InitCase.__init__].c(*op.exclusions[tm.InitCase.__init__].args)
    op.c(*op.args)

with OnePatch(tm.InitCase.use_attrs_inited_in__init, exclude_set={'InitCase.__init__'}) as op:
    op.exclusions[tm.InitCase.__init__].c(*op.exclusions['InitCase.__init__'].args)
    op.c(*op.args)
# endregion exclude_set
```

Exception classes will be excluded. You can use `include_set` to force patch this classes.

```py
import pytest
from one_patch import OnePatch
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_skip_exception_classes():
    with OnePatch(tm.raise_some_exception) as op:
        # SomeException will not be mocked be default
        with pytest.raises(tm.SomeException):
            op.c(*op.args)

    with OnePatch(tm.raise_some_exception, include_set={'SomeException'}) as op:  # force mock SomeException
        # raise SomeException, if SomeException is a mock object, will produce TypeError
        with pytest.raises(TypeError):  
            op.c(*op.args)
```

## Shortcuts

`Op` is the same as `OnePatch`.

```py
from one_patch import Op  # Op is a shortcut for OnePatch
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_op_shortcut__success_method():
    with Op(tm.FirstClass.success_method) as op:
        op.c(*op.args)
```

`Ol` is `Op` + `PatchLogger`.

```py
from one_patch import Op, PatchLogger
import one_patch.testing_fixtures as tm  # tm means `testing module`

# this long way may be shorter
with Op(tm.FirstClass.success_method) as (op, c, args, s):
    with PatchLogger(tm.logger) as logger:
        result = c(*args)
```

```py
from one_patch import Ol
import one_patch.testing_fixtures as tm  # tm means `testing module`

with Ol(tm.FirstClass.success_method) as (op, c, args, s):
    result = c(*args)  # Ol already included PatchLogger
```

`Oc` automatically perform `r = op.c(*op.args)`. 
Use `Oc` instead of `Op` or `OnePatch`. 
This is more short and convenient way.

```py
from one_patch import Oc, m  # 'm' is a shortcut for `typing.cast(Mock, something)`
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_oc_shortcut__success_method():
    with Oc(tm.FirstClass.success_method) as oc:  # `Oc` makes `op.c(*op.args)` automatically
        # do not need `r = op.c(*op.args)`
        assert oc.r == m(tm.failed_function).return_value  # `oc.r` is a result of `op.c(*op.args)`
```

`Ocl` like `Oc`, it automatically does `r = op.c(*op.args)`.
Also, it uses `PatchLogger` and exclude `logging` and `logger` identifiers in the testing module.

Thus, code below can be more short.

```py
from one_patch import OnePatch, PatchLogger
import one_patch.testing_fixtures as tm

def test_do_log_debug_success():
    with OnePatch(tm.do_log_debug_success, exclude_set={'logging', 'logger'}) as op:
        with PatchLogger(tm.logger):
            assert op.c(*op.args) is None
```

Like this.

```py
from one_patch import Ocl
import one_patch.testing_fixtures as tm  # tm means `testing module`

def test_do_log_debug_success__via_shortcut():
    with Ocl(tm.do_log_debug_success):
        pass
```

Note: `Ocl` works only if your testing module imports `logging` and creates a logger with identifier name `logger`.

```py
# testing module
import logging  # Ocl requires
logger = logging.getLogger('my_logger')  # Ocl requires
```

## Examples

Please, look `pytest__one_patch`, self-documented file contains the most usage examples, 
those checks `OnePatch` using `OnePatch` itself.

More useful examples:
- TestOnePatch.test_success_method
- TestOnePatch.test_success_class_method
- TestOnePatch.test_use_attrs_inited_in__init

## Bonus

All mocks created by `OnePatch` created with `autospec`. 
So your tests will defend your code against a human factor in the future, like a dirty refactoring.
