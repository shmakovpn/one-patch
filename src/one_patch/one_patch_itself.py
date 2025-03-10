from typing import Callable, List, ContextManager, Set, Optional, Dict, NewType, Union, Any, cast
from types import ModuleType
import logging
import dataclasses
import sys
import inspect
from unittest.mock import Mock, patch, MagicMock
from .patch_logger import PatchLogger

__all__ = (
    'ArgumentName',
    'ArgumentIndex',
    'IdentifierName',
    'IdentifierPath',
    'ArgsKwargs',
    'OnePatchDTO',
    'OnePatch',
    'Op',
    'Ol',
    'ResultOnePatchDTO',
    'Oc',
    'Ocl',
)

ArgumentName = NewType('ArgumentName', str)
"""
The name of an argument if function or method signature.

example:

```py
def my_func(self, x):
    # ArgumentName('self') the name of the argument with ArgumentIndex(0)
    # ArgumentName('x) the name of the argument with ArgumentIndex(1)
    pass
```
"""

ArgumentIndex = NewType('ArgumentIndex', int)
"""
The index of argument in order of a method or a function signature

example:

```py
def my_func(self, x):
    # ArgumentIndex(0) the index of the ArgumentName('self') argument
    # ArgumentIndex(1) the index of the ArgumentName('x') argument
    pass
```
"""

IdentifierName = NewType('IdentifierName', str)
"""
The name of python (identifier) variable in a scope 
"""

IdentifierPath = NewType('IdentifierPath', str)
"""
The python path to identifier
"""


class ArgsKwargs(list):
    """
    Container for `*args` and `**kwargs` based in list.

    Usage example:

    ```py
    m0 = MagicMock()
    m1 = MagicMock()

    args_kwargs = ArgsKwargs()
    args_kwargs.add_argument(argument_name=ArgumentName('self'), argument_value=m0)
    args_kwargs.add_argument(argument_name=ArgumentName('x'), argument_value=m1)

    assert args_kwargs[0] is m0
    assert args_kwargs.self is m0

    assert args_kwargs[1] is m1
    assert args_kwargs.x is m1

    # you can unpack ArgsKwargs
    # `c(*args_kwargs)` the same as `c(m0, m1)`
    ```
    """
    _index_map: Dict[ArgumentName, ArgumentIndex] = {}  # {'argument name': argument index}

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._index_map: Dict[ArgumentName, ArgumentIndex] = {}

    def __getattr__(self, item: str) -> MagicMock:
        try:
            return super().__getitem__(self._index_map[ArgumentName(item)])
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key: str, value: MagicMock):
        if key not in dir(self):
            super().__setitem__(self._index_map[ArgumentName(key)], value)
        else:
            super().__setattr__(key, value)

    def add_argument(self, argument_name: ArgumentName, argument_value: MagicMock) -> None:
        """Adds argument and its value to this list"""
        self._index_map[argument_name] = ArgumentIndex(len(self._index_map))
        super().append(argument_value)


@dataclasses.dataclass
class CallableDTO:
    """Information of excluded from patching (mocking) callable object"""
    args: ArgsKwargs
    """
    The list of arguments, 
    including `self` for methods (args[0] or args.self) and `cls` for class-methods (args[0] or args.cls)
    """
    c: Callable
    """callable, you have to call in your unit-test like: `op.c(*op.args)`"""


@dataclasses.dataclass
class NotCallableDTO:
    """Information of excluded from patching (mocking) not_callable object"""
    o: Any
    """excluded object itself"""


@dataclasses.dataclass
class OnePatchDTO:
    """
    Patching result. Mock arguments and callable to call.
    """

    args: ArgsKwargs
    """
    The list of arguments, 
    including `self` for methods (args[0] or args.self) and `cls` for class-methods (args[0] or args.cls)
    """
    c: Callable
    """callable, you have to call in your unit-test like: `op.c(*op.args)`"""
    exclusions: Dict[Union[Callable, IdentifierPath, str], Union[CallableDTO, NotCallableDTO]]
    """The list of arguments for excluded callable"""

    def __iter__(self):
        """
        with OnePatch(f) as (op, c, args, s):
            assert op.c == c
            assert op.args == args
            assert op.args.self == s  # or assert op.args.cls == s
        """
        yield self
        yield self.c
        yield self.args
        yield getattr(self.args, 'self', getattr(self.args, 'cls', None))


class FakeModule:
    def __init__(self, tm):
        self.tm = tm


class OnePatch:
    """
    One patch context manager. Creates mock scope, mock argument list and give your callable to call
    in your unit-test, extracted from testing method or function

    example:

    ```py
    # pytests/pytest__my_module.py

    import my_module as tm  # testing module
    from one_patch import OnePatch

    with OnePatch(tm.my_func) as oc:
        # all scope around of tm.my_func will be mocked
        # op.c - callable you need to use in your unit-tests
        # op.args - mocked argument list you need to use in your unit-tests
        result = op.c(*op.args)  # call testing method or function
        # your asserts
    ```
    """

    _include_set: Set[Union[IdentifierName, IdentifierPath]] = {IdentifierName('id')}
    """
    Identifiers (variables) names or qualified names which have to be mocked

    example:

    ```py
    with OnePatch(tm.my_func, include_set={'type'}) as oc:
        # `tm.type` will be a MagicMock in the testing module `tm`
        result = op.c(*op.args)
        assert tm.type.assert_called()  # do asserts with mocked `type`
        tm.something.assert_called_once_with(type_=tm.type.return_value)  # using mocked `type` return value
    ```
    """
    _exclude_set: Set[Union[IdentifierName, IdentifierPath, Callable]] = set()
    """
    Identifiers (variables) names or objects which have to be excluded from mocking

    example:

    ```py
    with OnePatch(tm.MyClass.my_method, exclude_set={'my_func', tm.MyClass.__init__}) as oc:
        # `tm.my_func` will not be mocked in the testing module `tm`
        result = op.c(*op.args)
        assert not isinstance(tm.my_func, Mock)
    ```
    """
    # region exclusions
    _exclude_identifier_set: Set[IdentifierName] = set()
    _exclude_path_set: Set[IdentifierPath] = set()
    _exclude_first_path_identifier_set: Set[IdentifierName] = set()
    _exclude_object_set: Set[Callable] = set()
    _exclude_object_path_set: Set[IdentifierPath] = set()
    _exclude_first_object_path_identifier_set: Set[IdentifierName] = set()
    # endregion exclusions

    def __init__(
        self,
        func: Callable,
        include_set: Optional[Set[Union[IdentifierName, IdentifierPath, str]]] = None,
        exclude_set: Optional[Set[Union[IdentifierName, IdentifierPath, Callable, str]]] = None
    ):
        """

        :param func: the method or the function around which will created all mocked scope (testing function or method)
        :param include_set: set of identifiers (variables) names, which need to be mocked, like: {'type'}
        :param exclude_set: set of identifiers (variables) names, which will excluding from mocking, like: {'my_func'}
          or set of object, which need to be excluded from mocking, like: {tm.FirstClass.__init__}
          or set of python paths, like {'FirstClass.__init__'}

        Note: exclude_set has more priority than include_set.
        """
        self._func: Callable = func
        """ testing function or method """
        self._patchers: List[ContextManager] = []
        """ Applied patchers in __enter__, to exit in __exit__ """

        if include_set:
            self._include_set: Set[Union[IdentifierName, IdentifierPath]] = (
                    self._include_set | cast(Set[Union[IdentifierName, IdentifierPath]], include_set)
            )
            """
            set of identifiers (variables) names, which need to be mocked, like: {'type'}
            """

        if exclude_set:
            self._exclude_set: Set[Union[IdentifierName, IdentifierPath, Callable]] = (
                    self._exclude_set | cast(Set[Union[IdentifierName, IdentifierPath, Callable]], exclude_set)
            )
            """
            set of identifiers (variables) names, which will excluding from mocking, like: {'my_func'}
            """
            self._init_exclusions()

    def _init_exclusions(self) -> None:
        exclude_path_set: Set[IdentifierPath] = {
            IdentifierPath(exclude_path) for exclude_path in self._exclude_set
            if isinstance(exclude_path, str) and '.' in exclude_path
        }
        exclude_first_path_identifier_set: Set[IdentifierName] = {
            IdentifierName(exclude_path.split('.')[0]) for exclude_path in self._exclude_set
            if isinstance(exclude_path, str) and '.' in exclude_path
        }
        exclude_identifier_set: Set[IdentifierName] = {
            IdentifierName(exclude_identifier) for exclude_identifier in self._exclude_set
            if isinstance(exclude_identifier, str) and '.' not in exclude_identifier
        }
        exclude_object_set: Set[Callable] = {
            exclude_object for exclude_object in self._exclude_set
            if not isinstance(exclude_object, str)
        }
        self._exclude_path_set: Set[IdentifierPath] = self._exclude_path_set | exclude_path_set
        self._exclude_identifier_set = self._exclude_identifier_set | exclude_identifier_set
        self._exclude_object_set = self._exclude_object_set | exclude_object_set
        self._exclude_object_path_set = {
            self._get_exclude_object_path(exclude_object=exclude_object)
            for exclude_object in self._exclude_object_set
        }
        self._exclude_first_path_identifier_set = (
            self._exclude_first_path_identifier_set | exclude_first_path_identifier_set
        )
        exclude_first_object_path_identifier_set: Set[IdentifierName] = {
            IdentifierName(exclude_object_path.split('.')[0]) for exclude_object_path in self._exclude_object_path_set
        }
        self._exclude_first_object_path_identifier_set = (
            self._exclude_first_object_path_identifier_set | exclude_first_object_path_identifier_set
        )

    def _get_testing_module(self) -> ModuleType:
        """Returns the module of the testing function or method"""
        module_path: str = getattr(self._func, '__module__')
        testing_module: ModuleType = sys.modules[module_path]
        return testing_module

    def __enter__(self) -> OnePatchDTO:
        testing_module: ModuleType = self._get_testing_module()
        fake_parent_module = FakeModule(tm=testing_module)

        patcher = patch.object(fake_parent_module, 'tm', autospec=True)
        self._patchers.append(patcher)
        mocked_module = patcher.__enter__()
        patching_list: List[MagicMock] = self.get_patching_list(test_method=self._func, mock_module=mocked_module)

        args_kwargs_dto: CallableDTO = self._get_args_and_callable(func=self._func, patching_list=patching_list)
        args: ArgsKwargs = args_kwargs_dto.args
        c: Callable = args_kwargs_dto.c

        self._patch_module_identifiers(
            testing_module=testing_module, mocked_module=mocked_module, patching_list=patching_list
        )
        self._patch_include_set(testing_module=testing_module)

        exclusions: Dict[Union[Callable, IdentifierPath, str], Union[CallableDTO, NotCallableDTO]] = {}
        all_exclude_set = self._exclude_path_set | self._exclude_object_path_set

        exclude_path: IdentifierPath
        for exclude_path in all_exclude_set:
            exclude_object: Callable = self._getattr_by_path(obj=testing_module, path=exclude_path)

            exclude_identifiers: List[IdentifierName] = cast(List[IdentifierName], exclude_path.split('.'))
            if len(exclude_identifiers) < 2:
                raise ValueError(f'len(exclude_identifiers)<2')

            if len(patching_list):
                parent_object: MagicMock = mocked_module

                idx: int
                exclude_identifier: IdentifierName
                for idx, exclude_identifier in enumerate(exclude_identifiers):
                    current_object = getattr(parent_object, exclude_identifier)

                    if len(patching_list) > idx and patching_list[idx] == current_object:
                        pass
                    else:
                        if idx < (len(exclude_identifiers) - 1):
                            patcher = patch.object(parent_object, exclude_identifier, current_object)
                        else:
                            if exclude_identifier == '__init__':
                                # it is not possible to set `__init__` attribute in MagicMock instance
                                # in case of `__init__` use `m__init__` instead
                                patcher = patch.object(
                                    parent_object,
                                    f'm{exclude_identifier}',
                                    cast(Mock, exclude_object),  # mypy hack
                                    create=True,
                                )
                            else:
                                patcher = patch.object(
                                    parent_object,
                                    exclude_identifier,
                                    cast(Mock, exclude_object),  # mypy hack
                                )

                            if callable(exclude_object):
                                callable_exclusion_dto: CallableDTO = self._get_args_and_callable(
                                    func=exclude_object,
                                    patching_list=[parent_object],
                                )
                                exclusions[exclude_object] = callable_exclusion_dto
                                exclusions[exclude_path] = callable_exclusion_dto
                            else:
                                not_callable_exclusion_dto: NotCallableDTO = NotCallableDTO(o=exclude_object)
                                # in case of not_callable object exclusion, we cannot put it as a key of
                                # the exclusion dict
                                # exclusions[exclude_object] = not_callable_exclusion_dto  # don't uncomment !!
                                exclusions[exclude_path] = not_callable_exclusion_dto

                        patcher.__enter__()
                        self._patchers.append(patcher)

                    parent_object = current_object

        return OnePatchDTO(args=args, c=c, exclusions=exclusions)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for patcher in reversed(self._patchers):
            patcher.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def _getattr_by_path(obj: Any, path: IdentifierPath) -> Callable:
        """
        example:

        ```py
        class X:
            class Y:
                t = 4

        print(getattr_by_path(X, 'Y.t'))  # prints 4
        ```
        """
        obj_ = obj

        for path_item in path.split('.'):
            obj_ = getattr(obj_, path_item)

        return obj_

    @staticmethod
    def _get_exclude_object_path(exclude_object: Callable) -> IdentifierPath:
        # noinspection SpellCheckingInspection
        exclude_object_path: Optional[IdentifierPath] = getattr(exclude_object, '__qualname__', None)
        if not exclude_object_path:
            # noinspection SpellCheckingInspection
            raise ValueError(f'exclude_object does not have attribute `__qualname__: {exclude_object}')

        return exclude_object_path

    @classmethod
    def _get_args_and_callable(cls, func: Callable, patching_list: List[MagicMock]) -> CallableDTO:
        args = ArgsKwargs()
        params = inspect.signature(func).parameters
        c: Callable = func

        if cls.is_class_method(class_method=func):
            c = getattr(func, '__func__')

            if len(patching_list):
                args.add_argument(argument_name=ArgumentName('cls'), argument_value=patching_list[-1])

            param_name: str
            for param_name in params.keys():
                args.add_argument(argument_name=ArgumentName(param_name), argument_value=MagicMock())
        else:
            param_name_: str
            for param_name_ in params.keys():
                if len(patching_list):
                    if param_name_ == 'self':
                        args.add_argument(argument_name=ArgumentName(param_name_), argument_value=patching_list[-1])
                    else:
                        args.add_argument(argument_name=ArgumentName(param_name_), argument_value=MagicMock())
                else:
                    args.add_argument(argument_name=ArgumentName(param_name_), argument_value=MagicMock())

        return CallableDTO(args=args, c=c)

    def _patch_module_identifiers(
        self,
        testing_module: ModuleType,
        mocked_module: MagicMock,
        patching_list: List[MagicMock]
    ):
        """ Move mocks from mocked_module to testing_module """
        identifier: IdentifierName  # The name of the attribute (variable) in the testing module
        for identifier, identifier_value in cast(Dict[IdentifierName, Any], testing_module.__dict__.copy()).items():
            all_exclude: Set[IdentifierName] = (
                self._exclude_identifier_set
                | self._exclude_first_path_identifier_set
                | self._exclude_first_object_path_identifier_set
            )

            if identifier in all_exclude:
                continue

            if (
                identifier.startswith('__')  # skip magics,
                and identifier not in self._include_set  # if identifier is set to be mocked explicitly
            ):
                continue

            if identifier_value is self._func:
                continue

            if isinstance(identifier_value, Mock):
                continue  # do not mock that has already mocked

            if inspect.isclass(identifier_value) and issubclass(identifier_value, Exception):
                continue  # skip exception classes

            if len(patching_list) and identifier == getattr(patching_list[0], '_mock_name'):
                continue  #

            identifier_patcher: ContextManager = patch.object(
                testing_module, identifier, getattr(mocked_module, identifier)
            )
            identifier_patcher.__enter__()
            self._patchers.append(identifier_patcher)

    def _patch_include_set(self, testing_module: ModuleType) -> None:
        """ patches identifiers in defined in include set """
        exclude_set: Set[Union[IdentifierName, IdentifierPath]]
        exclude_set = self._exclude_identifier_set | self._exclude_path_set | self._exclude_object_path_set

        include_set: Set[Union[IdentifierName, IdentifierPath]]
        include_set = self._include_set - exclude_set  # exclude_set has more priority than include_set

        identifier_path: Union[IdentifierName, IdentifierPath]
        for identifier_path in include_set:

            parent = testing_module

            identifier: IdentifierName
            for identifier in cast(List[IdentifierName], identifier_path.split('.')[:-1]):
                parent = getattr(parent, identifier)

            if isinstance(getattr(parent, identifier_path.split('.')[-1], None), Mock):
                # noinspection SpellCheckingInspection
                continue  # python 3.10 does not support autospec on that already mocked

            patcher = patch.object(parent, identifier_path.split('.')[-1], create=True)
            patcher.__enter__()
            self._patchers.append(patcher)

    @classmethod
    def is_class_method(cls, class_method: Callable) -> bool:
        """ True if method is classmethod, otherwise False """
        is_class_method: bool = inspect.ismethod(class_method)
        return is_class_method

    @classmethod
    def get_patching_list(cls, test_method: Callable, mock_module: MagicMock) -> List[MagicMock]:
        """
        MagicMock-и от [testing_module, [class1, [class2, [...]]]]

        example:

        ```py
        # module
        class FirstClass:
            class SecondClass:
                def testing_method(self, x):
                    pass

        # patching_list for testing method will be:
        [
          MagickMock for testing_module,
          MagickMock for FirstClass,
          MagickMock for SecondClass
        ]
        ```
        """
        qualified_name: str = test_method.__qualname__

        patching_list: List = []
        names: List[str] = qualified_name.split('.')[:-1]
        current_object = mock_module

        name: str
        for name in names:
            current_object = getattr(current_object, name)
            patching_list.append(current_object)

        return patching_list


class Op(OnePatch):
    """ shortcut for OnePatch. """
    pass


class Ol(Op):
    """
    Shortcut for OnePatch + PatchLogger

    ```py
    # this long way may be shorter
    with Op(tm.f) as (op, c, args, s):
        with PatchLogger(tm.logger) as logger:
            result = c(*args)
    ```

    ```py
    with Ol(tm.f) as (op, c, args, s):
        result = c(*args)
    ```
    """
    def __enter__(self) -> OnePatchDTO:
        testing_module: ModuleType = self._get_testing_module()
        logger_: logging.Logger = getattr(testing_module, 'logger')
        self._patch_logger_manager = PatchLogger(logger=logger_).__enter__()
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._patch_logger_manager:
            self._patch_logger_manager.__exit__(None, None, None)
            self._patch_logger_manager = None
        super().__exit__(exc_type, exc_val, exc_tb)


@dataclasses.dataclass
class ResultOnePatchDTO(OnePatchDTO):
    """OnePatchDTO with result of `op.c(*op.args)`"""
    r: Any
    """result of `op.c(*op.args)`"""

    def __iter__(self):
        """
        with Oc(f) as r, op, c, args, s:
            assert op.c == c
            assert op.args == args
            assert op.args.self == s  # or assert op.args.cls == s
        """
        yield self.r
        yield from super().__iter__()


class Oc(Op):
    """
    `Oc` automatically perform `r = op.c(*op.args)`.
    Its `__enter__` returns `ResultOnePatchDTO` which `r` attribute contains the result of `op.c(*op.args)`.
    Thus, `Oc` is more short version of `OnePatch`.
    """
    def __enter__(self) -> ResultOnePatchDTO:
        op: OnePatchDTO = super().__enter__()

        try:
            result = op.c(*op.args)
        except Exception:
            self.__exit__(None, None, None)
            raise
        else:
            oc = ResultOnePatchDTO(r=result, args=op.args, c=op.c, exclusions=op.exclusions)
            return oc


class Ocl(Op):
    """
    `Ocl` extends `OnePatch` for testing code, that including logging.
    `Ocl` work like `Oc`, it performs `r = op.c(*op.args)` automatically.
    It is very easy to make a mistake in message template and other arguments, like `logger.debug("%s-%s", arg1)`.
    This code will produce `TypeError: not enough arguments for format string`. We need to patch `debug` method.

    Long example, without Ocl
    ```py
    def test_do_log_debug_success(self):
        with OnePatch(tm.do_log_debug_success, exclude_set={'logging', 'logger'}) as oc:
            with PatchLogger(tm.logger):
                assert op.c(*op.args) is None
    ```

    Sort example.
    ```py
    ```
    """
    _patch_logger_manager: Optional[PatchLogger] = None

    def __init__(
        self,
        func: Callable,
        include_set: Optional[Set[Union[IdentifierName, IdentifierPath, str]]] = None,
        exclude_set: Optional[Set[Union[IdentifierName, IdentifierPath, Callable, str]]] = None
    ):
        exclude_set_: Set[Union[IdentifierName, IdentifierPath, Callable, str]] = {
            IdentifierName('logging'),
            IdentifierName('logger'),
        }

        if exclude_set is not None:
            exclude_set_ = exclude_set_ | exclude_set

        super().__init__(func=func, include_set=include_set, exclude_set=exclude_set_)

    def __enter__(self) -> ResultOnePatchDTO:
        op: OnePatchDTO = super().__enter__()
        testing_module: ModuleType = self._get_testing_module()
        logger_: logging.Logger = getattr(testing_module, 'logger')
        self._patch_logger_manager = PatchLogger(logger=logger_).__enter__()

        try:
            result = op.c(*op.args)
        except Exception:
            self.__exit__(None, None, None)
            raise
        else:
            oc = ResultOnePatchDTO(r=result, args=op.args, c=op.c, exclusions=op.exclusions)
            return oc

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._patch_logger_manager is not None:
            self._patch_logger_manager.__exit__(None, None, None)
            self._patch_logger_manager = None
        super().__exit__(exc_type, exc_val, exc_tb)
