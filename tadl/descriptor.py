from typing import Generic, TypeVar, Callable

from tadl.types import TSelf

T = TypeVar("T")


class LazyInitDescriptor(Generic[T]):
    """
    A Python descriptor(*) object that calls the provided function to initialize
    the attribute on the instance when it's first accessed.

    (*) A descriptor is a class that implements the `__get__` method. When
    accessed through an instance, the descriptor's `__get__` method is called
    with the instance and class as arguments. This allows the descriptor to
    control how the attribute is accessed.
    https://docs.python.org/3/howto/descriptor.html
    """

    def __init__(self, fn: Callable[[TSelf], T]) -> None:
        self.__fn = fn

    def __set_name__(self, owner: type, name: str) -> None:
        # __set_name__ is invoked at the end of the class definition body.
        self.__name = name

    def __get__(self, instance: TSelf, owner: type) -> T:
        """
        On the first property access, we construct the desired object and then
        set the attribute on the instance. Because the descriptor lives on the
        class, and the attribute lives on the instance, subsequent access to the
        property will use the instance attribute value we set here instead of
        the class attribute.

        # Example

            value = 0
            class Foo:
                # The Descriptor is a class attribute
                bar = Descriptor(lambda self: f"{self.__class__.__name__} with {value}")

            f = Foo()

            # The __dict__ is empty because the class has no attributes set during
            # __init__.
            print(f.__dict__)

            # The object's dir does include `bar` because it's an attribute on the
            # object's class.
            print(dir(f))

            # The first access to the property will attempt to lookup "bar", find
            # the class attribute (which is an instance of `Descriptor`), and invoke
            # the __get__ method on it which constructs the desired value.
            print(f.bar)  # Foo with 0

            # The first access assigns the attribute name to the object which
            # inserts it into the object's __dict__.
            print(f.__dict__)  # {'bar': 'Foo with 0'}

            # Subsequent accesses will use the instance attribute value (from the
            # object's __dict__) instead of the class attribute value.
            value = 1
            print(f.bar)  # "Foo with 0"

            # Deleting the instance attribute and then accessing it will re-invoke
            # the __get__ method on the `Descriptor`.
            # (This isn't an expected use case, it's just here for illustration.)
            del f.bar
            value = 2
            print(f.bar)  # "Foo with 2"
        """
        if instance is None:
            raise ValueError("Descriptor must be accessed through an instance.")
        value = self.__fn(instance)
        setattr(instance, self.__name, value)
        return value
