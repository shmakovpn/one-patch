from typing import cast
import pytest
from unittest.mock import NonCallableMock, Mock, MagicMock, patch
from one_patch import (
    OnePatch,
    ArgsKwargs,
    ArgumentName,
    IdentifierName,
    m,
    Op,
    Oc,
    Ocl,
)
import one_patch.testing_fixtures as tm
from one_patch.patch_logger import PatchLogger


"""
TLDR: We recommended to look at `test_success_method`, and `test_success_class_method`, because it more basic.
test_success_method, test_success_class_method is enough to write your first unit-tests based on OnePatch.

These are very short, it covered tested methods to 100%.
Please. look at the basic test structure, that represents the minimal successfully test without asserts.
Wow!! Only three lines, including `def test_success_method(self):`, it is amazing.

```py
    def test_success_method(self):
        with OnePatch(tm.FirstClass.success_method) as op:
            r = op.c(*op.args)
            # your asserts here
```
"""


class TestOnePatch:
    """
    Unit-tests for OnePatch itself and at the same time helpful examples, how to work this OnePatch.

    Here we will test `one_patch_data/testing_fixtures.py` module
    """

    def test_module_const(self):
        """
        All identifiers (variables) in testing module `one_patch_data/testing_fixtures.py` have to be mocked,
        including string constant `MODULE_CONST`.

        Let's check, that `MODULE_CONST` become a Mock
        """
        with OnePatch(tm.FirstClass.success_method):
            assert isinstance(tm.MODULE_CONST, NonCallableMock)

    def test_first_class_const(self):
        """
        All attributes in classes in testing module `one_patch_data/testing_fixtures.py` have to be mocked,
        including string constant `FirstClass.first_class_const`.

        Let's check, that `FirstClass.first_class_const` become a Mock.
        """
        with OnePatch(tm.FirstClass.success_method) as op:
            assert isinstance(op.args[0].first_class_const, NonCallableMock)

    def test_second_class__second_class_const(self):
        """
        All attributes in internal class in `testing module.FistClass.SecondClass` have to be mocked,
        including string constant `FirstClass.SecondClass.second_class_const`.
        This mocking is not performing directly, see comments in this test, to learn how to access to mocked attributes.

        Let's check, that `FirstClass.SecondClass.second_class_const` become a Mock.
        """
        with OnePatch(tm.FirstClass.success_method) as op:
            # Note: op.args[0] == op.args.self
            # if you need access to mocked `FirstClass.SecondClass.second_class_const`,
            # you have to use op.args[0] or op.args.self
            # Please: don't use `tm.FirstClass.SecondClass.second_class_const`,
            # because classes that are in path to testing method
            # are not mocked in `testing module` to stay access for original classes for future.
            assert isinstance(op.args[0].SecondClass.second_class_const, NonCallableMock)

    def test_second_class(self):
        """
        All classes in path to testing method have to be mocked,
        including `FirstClass.SecondClass`.
        This mocking is not performing directly, see comments in this test, to learn how to access to mocked attributes.

        Let's check, that `FirstClass.SecondClass` become a Mock.
        """
        with OnePatch(tm.FirstClass.success_method) as op:
            # Note: op.args[0] == op.args.self
            # if you need access to mocked `FistClass.SecondClass`
            # you have to use op[0] or op.args.self
            # Please: don't use `tm.FirstClass.SecondClass`,
            # because classes that are in path to testing method
            # are not mocked in `testing module` to stay access for original classes for future.
            assert isinstance(op.args[0].SecondClass, Mock)

    def test_success_method(self):
        """
        Full test (with 100% coverage) for `success_method`.

        In this case `success_method` calls other functions that fails.
        But the `success_method` itself does not contain errors, so this test must be performed successfully.
        """
        with OnePatch(tm.FirstClass.success_method) as op:
            r = op.c(*op.args)
            assert r == cast(Mock, tm.failed_function).return_value
            cast(Mock, tm.failed_function).assert_called_once_with(tm.id.return_value)  # noqa
            # Note: op.args[0] == op.args.self
            # In the case of `FirstClass.success_method`, see method signature,
            # one can access to mocked `method_argument` like `op.args[1]` or `op.args.method_argument`.
            cast(Mock, getattr(tm, 'id')).assert_called_once_with(op.args.method_argument)

            # Please, don't use `tm.FirstClass.failed_method`, because class that are in path to testing method
            # are not mocked in `testing_module` to stay access for original classes for future
            # use `op.args.self.failed_method` or `op.args[0].failed_method` instead
            cast(Mock, op.args.self.failed_method).assert_called_once_with(1, 2)
            cast(Mock, op.args[0].failed_class_method).assert_called_once_with(1, 2)
            cast(Mock, op.args[0].failed_static_method).assert_called_once_with(1, 2)

    def test_success_class_method(self):
        """
        Full test (with 100% coverage) for `success_class_method`.

        In this case `success_class_method` calls other functions that fails.
        But the `success_class_method` itself does not contain errors, so this test must be performed successfully.
        """
        with OnePatch(tm.FirstClass.success_class_method) as op:
            r = op.c(*op.args)
            assert r == cast(Mock, tm.failed_function).return_value
            # None: op.args[0] == op.args.cls
            # In the case of `FirstClass.success_class_method`, see method signature,
            # one can access to mocked `class_method_argument` like `op.args[1]`
            # or `op.args.class_method_argument`
            cast(Mock, tm.id).assert_called_once_with(op.args.class_method_argument)  # noqa

            # Please, don't use `tm.FirstClass.failed_class_method`,
            # because class that are in path to testing class method are not mocked in `testing_module`
            # to stay access for original classes for future
            # user `op.args.cls.failed_class_method` or `op.args[0].failed_class_method`
            cast(Mock, op.args.cls.failed_class_method).assert_called_once_with(1, 2)
            cast(Mock, op.args[0].failed_static_method).assert_called_once_with(1, 2)
            cast(Mock, tm.failed_function).assert_called_once_with(tm.id.return_value)  # noqa

    def test_success_static_method(self):
        """
        Minimal test (without asserts) for `success_static_method`.

        In this case `success_static_method` calls other functions that fails.
        But the `success_static_method` itself does not contain errors, so this test must be performed successfully.
        """
        with OnePatch(tm.FirstClass.success_static_method) as op:
            _r = op.c(*op.args)

    def test_fail_method__failed_function(self):
        """
        Minimal test (without asserts) for `fail_method__failed_function`.

        In this case `fail_method__failed_function` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_method__failed_function) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_method__failed_method(self):
        """
        Minimal test (without asserts) for `fail_method__failed_method`.

        In this case `fail_method__failed_method` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_method__failed_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_method__failed_class_method(self):
        """
        Minimal test (without asserts) for `fail_method__failed_class_method`.

        In this case `fail_method__failed_class_method` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_method__failed_class_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_method__failed_static_method(self):
        """
        Minimal test (without asserts) for `fail_method__failed_static_method`.

        In this case `fail_method__failed_static_method` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_method__failed_static_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_class_method__failed_function(self):
        """
        Minimal test (without asserts) for `fail_class_method__failed_function`.

        In this case `fail_class_method__failed_function` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_class_method__failed_function) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_class_method__failed_class_method(self):
        """
        Minimal test (without asserts) for `fail_class_method__failed_class_method`.

        In this case `fail_class_method__failed_class_method` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_class_method__failed_class_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_class_method__failed_static_method(self):
        """
        Minimal test (without asserts) for `fail_class_method__failed_static_method`.

        In this case `fail_class_method__failed_static_method` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_class_method__failed_static_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_static_method__failed_function(self):
        """
        Minimal test (without asserts) for `fail_static_method__failed_functions`.

        In this case `fail_static_method__failed_functions` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.fail_static_method__failed_functions) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_some_property(self):
        """
        Minimal test (without asserts) for `FirstClass.some_property`.

        Use `fget` attribute of `property` to get value of `some_property`
        """
        with OnePatch(tm.FirstClass.some_property.fget) as op:
            assert op.c(*op.args) == 'hello'

    def test_second_success_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_success_method`

        In this case `FirstClass.SecondClass.second_success_method` calls other functions that fails.
        But the `FirstClass.SecondClass.second_success_method` itself does not contain errors,
        so this test must be performed successfully.
        """
        with OnePatch(tm.FirstClass.SecondClass.second_success_method) as op:
            op.c(*op.args)

    def test_second_success_class_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_success_class_method`

        In this case `FirstClass.SecondClass.second_success_class_method` calls other functions that fails.
        But the `FirstClass.SecondClass.second_success_class_method` itself does not contain errors,
        so this test must be performed successfully.
        """
        with OnePatch(tm.FirstClass.SecondClass.second_success_class_method) as op:
            op.c(*op.args)

    def test_second_success_static_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_success_static_method`

        In this case `FirstClass.SecondClass.second_success_static_method` calls other functions that fails.
        But the `FirstClass.SecondClass.second_success_static_method` itself does not contain errors,
        so this test must be performed successfully.
        """
        with OnePatch(tm.FirstClass.SecondClass.second_success_static_method) as op:
            op.c(*op.args)

    def test_second_fail_method__failed_function(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_method__failed_function`

        In this case `FirstClass.SecondClass.second_fail_method__failed_function`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_method__failed_function) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_second_fail_method__failed_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_method__failed_method`

        In this case `FirstClass.SecondClass.second_fail_method__failed_method`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_method__failed_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_second_fail_method__failed_class_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_method__failed_class_method`

        In this case `FirstClass.SecondClass.second_fail_method__failed_class_method`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_method__failed_class_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_second_fail_method__failed_static_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_method__failed_static_method`

        In this case `FirstClass.SecondClass.second_fail_method__failed_static_method`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_method__failed_static_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_second_fail_class_method__failed_function(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_class_method__failed_function`

        In this case `FirstClass.SecondClass.second_fail_class_method__failed_function`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_class_method__failed_function) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_second_fail_class_method__failed_class_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_class_method__failed_class_method`

        In this case `FirstClass.SecondClass.second_fail_class_method__failed_class_method`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_class_method__failed_class_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_second_fail_class_method__failed_static_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_class_method__failed_static_method`.

        In this case `FirstClass.SecondClass.second_fail_class_method__failed_static_method`
        calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_class_method__failed_static_method) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_success_function(self):
        """
        Minimal test (without asserts) for `success_function`.

        In this case `success_function` calls other functions that fails.
        But the `success_function` itself does not contain errors,
        so this test must be performed successfully.
        """
        with OnePatch(tm.success_function) as op:
            op.c(*op.args)

    def test_fail__failed_function(self):
        """
        Minimal test (without asserts) for `fail__failed_function`.

        In this case `fail__failed_function` calls other function with wrong signature.
        Here we catch `TypeError` that raised when trying to call a MagicMock callable with wrong signature
        """
        with OnePatch(tm.fail__failed_function) as op:
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_fail_no_method(self):
        """
        Minimal test (without asserts) for `FirstClass.fail_no_method`.

        In this case `FirstClass.fail_no_method` try to call a method that does not exist.
        Here we catch `AttributeError`.
        """
        with OnePatch(tm.FirstClass.fail_no_method) as op:
            with pytest.raises(AttributeError):
                op.c(*op.args)

    def test_fail_no_function(self):
        """
        Minimal test (without asserts) for `FirstClass.fail_no_function`.

        In this case `FirstClass.fail_no_function` try to call a global function that does not exist.
        Here we catch `NameError`.
        """
        with OnePatch(tm.FirstClass.fail_no_function) as op:
            with pytest.raises(NameError):
                op.c(*op.args)

    def test_fail_no_function1(self):
        """
        Minimal test (without asserts) for `fail_no_function1`.

        In this case `fail_no_function1` try to call a global function that does not exist.
        Here we catch `NameError`.
        """
        with OnePatch(tm.fail_no_function1) as op:
            with pytest.raises(NameError):
                op.c(*op.args)

    def test_second_fail_no_method(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_no_method`.

        In this case `FirstClass.SecondClass.second_fail_no_method` try to call a method that does not exist.
        Here we catch `AttributeError`.
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_no_method) as op:
            with pytest.raises(AttributeError):
                op.c(*op.args)

    def test_second_fail_no_function(self):
        """
        Minimal test (without asserts) for `FirstClass.SecondClass.second_fail_no_function`.

        In this case `FirstClass.SecondClass.second_fail_no_function` try to call a function that does not exist.
        Here we catch `NameError`.
        """
        with OnePatch(tm.FirstClass.SecondClass.second_fail_no_function) as op:
            with pytest.raises(NameError):
                op.c(*op.args)

    def test_success_static_method__include(self):
        """
        We put `type` in `include_set`,
        then `type` called in `FirstClass.success_static_method__include` will be mocked,
        after we checks that `type` was a MagicMock
        """
        with OnePatch(tm.FirstClass.success_static_method__include, include_set={IdentifierName('type')}) as op:
            r = op.c(*op.args)
            assert r == m(m(tm).type).return_value

    def test_success_static_method__exclude(self):
        """
        `id` is mocked by default.
        Here we put `id` to `exclude_set`. After checks, that `id` was not mocked and return an integer, not a Mock
        """
        with OnePatch(tm.FirstClass.success_static_method__exclude, exclude_set={'id'}) as op:
            r = op.c(*op.args)
            assert isinstance(r, int)

    def test_use_attrs_inited_in__init(self):
        """
        `x` and `y` attribute creates in `__init__`, these are not attributes of the class,
        and can not be mocked by default using `autospec=True`.
        `tm.InitCase.use_attrs_inited_in__init` try to access these attributes, so `AttributeError` will raise.

        Solutions:
          0. Refactoring, create these attributes in class `InitCase`:
            ```py
            class InitCase:
                x = None
                x = None
            ```
          1. create needed mocks manually - expensive way
            1.1 create needed mocks after patch - more short expensive way
          2. run `__init__` before run testing method
          3. put `__init__` in `exclude_set`, when run it before testing method
        """
        # region default_attribute_error
        with OnePatch(tm.InitCase.use_attrs_inited_in__init) as op:
            with pytest.raises(AttributeError):
                op.c(*op.args)  # by default will `AttributeError`
        # endregion default_attribute_error

        # region expensive_way
        # You have to mock all attributes of an instance of the class using in testing method.
        # This way may be expensive
        # Note: here we use 40 and 50, not mock objects, because in python3.10 will 'Cannot autospec a Mock object'
        with patch.object(tm.InitCase, 'x', 40, create=True):  # mock 1
            with patch.object(tm.InitCase, 'y', 50, create=True):  # mock 2
                with OnePatch(tm.InitCase.use_attrs_inited_in__init) as op:
                    op.c(*op.args)
        # endregion expensive_way

        # region more_short_expensive_way
        with OnePatch(tm.InitCase.use_attrs_inited_in__init) as op:
            op.args.self.x = Mock()  # the same as `with patch.object(tm.InitCase, 'x', create=True)`
            op.args.self.y = Mock()  # the same as `with patch.object(tm.InitCase, 'y', create=True)`
            op.c(*op.args)
        # endregion more_short_expensive_way

        # region run_init_before
        with OnePatch(tm.InitCase.__init__) as op:
            init_op = op

        assert not isinstance(tm.InitCase.__init__, NonCallableMock)

        with OnePatch(tm.InitCase.use_attrs_inited_in__init) as op:
            tm.InitCase.__init__(op.args.self, *init_op.args[1:])  # noqa
            op.c(*op.args)
        # endregion run_init_before

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

    def test_exclusions(self):
        with OnePatch(tm.FirstClass.success_method, exclude_set={'FirstClass.first_class_const'}) as op:
            assert op.exclusions['FirstClass.first_class_const'].o

        with OnePatch(tm.FirstClass.success_method, exclude_set={'FirstClass.failed_method'}) as op:
            assert op.exclusions['FirstClass.failed_method'].c
            assert op.exclusions[tm.FirstClass.failed_method].c

        with OnePatch(tm.FirstClass.success_method, exclude_set={tm.FirstClass.failed_method}) as op:
            assert op.exclusions['FirstClass.failed_method'].c
            assert op.exclusions[tm.FirstClass.failed_method].c

    def test_do_log_debug_success(self):
        with OnePatch(tm.do_log_debug_success, exclude_set={'logging', 'logger'}) as op:
            with PatchLogger(tm.logger):
                assert op.c(*op.args) is None

    def test_do_log_debug_fail(self):
        with OnePatch(tm.do_log_debug_fail, exclude_set={'logging', 'logger'}) as op:
            with PatchLogger(tm.logger):
                with pytest.raises(TypeError):
                    assert op.c(*op.args) is None

    def test_do_log_debug_success__via_shortcut(self):
        with Ocl(tm.do_log_debug_success):
            pass

    def test_do_log_debug_fail__via_shortcut(self):
        with pytest.raises(TypeError):
            with Ocl(tm.do_log_debug_fail):
                pass

    def test_op_dto_unpack(self):
        with OnePatch(tm.FirstClass.success_method) as (op, c, args, s):
            assert op.c == c
            assert op.args == args
            assert op.args.self == s

        with OnePatch(tm.FirstClass.success_class_method) as (op, c, args, cls):
            assert op.c == c
            assert op.args == args
            assert op.args.cls == cls

        with OnePatch(tm.FirstClass.success_static_method) as (op, c, args, s):
            assert op.c == c
            assert op.args == args
            assert s is None
        # check short form
        with OnePatch(tm.FirstClass.success_static_method) as (op, c, *_):
            assert op.c == c

        with OnePatch(tm.FirstClass.success_method) as (op, *_, s):
            assert op.args.self == s

    def test_skip_exception_classes(self):
        with OnePatch(tm.raise_some_exception) as op:
            # SomeException will not be mocked be default
            with pytest.raises(tm.SomeException):
                op.c(*op.args)

        with OnePatch(tm.raise_some_exception, include_set={'SomeException'}) as op:
            # raise SomeException, if SomeException is a mock object, will produce TypeError
            with pytest.raises(TypeError):
                op.c(*op.args)

    def test_classes_with_mocks(self):
        """Test class with mocks can be patched"""
        with OnePatch(tm.ClassWithMocks.some_method) as op:
            assert op.c(*op.args) == 'hello ClassWithMocks'

    def test_op_shortcut__success_method(self):
        """
        Test `success_method` using `Op` shortcut instead of `OnePatch`.
        """
        with Op(tm.FirstClass.success_method) as op:
            op.c(*op.args)

    def test_rc_shortcut__success_method(self):
        """
        `Oc` automatically perform `r = op.c(*op.args)`.
        """
        with Oc(tm.FirstClass.success_method) as oc:
            # do not need `r = op.c(*op.args)`
            assert oc.r == m(tm.failed_function).return_value

    def test_rc_dto_unpack(self):
        """
        Use `Oc` instead of `Op` or `OnePatch`.
        This is more short and convenient way.
        """
        with Oc(tm.FirstClass.success_method) as (r, oc, c, args, s):
            assert oc.r == r
            assert oc.c == c
            assert oc.args == args
            assert oc.args.self == s

        with Oc(tm.FirstClass.success_class_method) as (r, oc, c, args, cls):
            assert oc.r == r
            assert oc.c == c
            assert oc.args == args
            assert oc.args.cls == cls

        with Oc(tm.FirstClass.success_static_method) as (r, oc, c, args, s):
            assert oc.r == r
            assert oc.c == c
            assert oc.args == args
            assert s is None
        # check short form
        with Oc(tm.FirstClass.success_static_method) as (r, oc, c, *_):
            assert oc.r == r
            assert oc.c == c

        with Oc(tm.FirstClass.success_method) as (r, oc, *_, s):
            assert oc.r == r
            assert oc.args.self == s


class TestArgsKwargs:
    def test_args_kwargs(self):
        args_kwargs = ArgsKwargs()
        args_kwargs.add_argument(ArgumentName('cls'), cast(MagicMock, '_cls'))
        args_kwargs.add_argument(ArgumentName('self'), cast(MagicMock, '_self'))
        args_kwargs.add_argument(ArgumentName('foo'), cast(MagicMock, '_foo'))
        args_kwargs.add_argument(ArgumentName('bar'), cast(MagicMock, '_bar'))
        assert args_kwargs.cls == '_cls'
        assert args_kwargs.self == '_self'
        assert args_kwargs.foo == '_foo'
        assert args_kwargs.bar == '_bar'

        assert args_kwargs[0] == '_cls'
        assert args_kwargs[1] == '_self'
        assert args_kwargs[2] == '_foo'
        assert args_kwargs[3] == '_bar'

        unpacked = [*args_kwargs]
        assert unpacked == ['_cls', '_self', '_foo', '_bar']

        # region setattr
        args_kwargs.foo = '_new_foo'
        assert args_kwargs.foo == '_new_foo'
        assert args_kwargs[2] == '_new_foo'
        # endregion setattr


class TestUtilsM:
    def test_m(self):
        """check that m is a shortcut for cast(Mock, arg)"""
        assert m('hello') == 'hello'
