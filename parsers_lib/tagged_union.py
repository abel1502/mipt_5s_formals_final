"""
Based on https://github.com/Carotti/tagged-union
"""

import typing
import dataclasses


Self: typing.Type = type("Self", (), dict(
    __doc__="""The type of the union itself."""
))


Unit: typing.Type = type("Unit", (), dict(
    __doc__="""Single-state type for tagged unions with no members."""
))


# _: typing.Type = type("_", (), dict(
#     __doc__="""A placeholder object for matching anything"""
# ))


def _is_classvar(value: typing.Any) -> bool:
    """
    Not great, but will have to do...
    """
    
    return value is typing.ClassVar or \
        (isinstance(value, typing._GenericAlias) and
         value.__origin__ is typing.ClassVar) or \
        (isinstance(value, str) and
         (value.startswith("typing.ClassVar") or 
          value.startswith("ClassVar")))


def tagged_union(cls: typing.Type) -> typing.Type:
    """
    Class decorator that creates a tagged union.
    """
    
    assert issubclass(cls, object)
    
    members = {}
    for name, value in cls.__annotations__.items():
        if name.startswith("__") or _is_classvar(value):
            continue
        
        if value is Self:
            value = cls
        
        ns: typing.Dict[str, typing.Any] = {}
        
        # This highlights the need for a proper type annotation processing api in the standard library.
        # For now I'll leave it like this, but it could theoretically fail if the user has their own
        # type named "Unit"
        if value is Unit or value == "Unit":
            ns["value"] = property(lambda self: None)
        else:
            ns["__annotations__"] = dict(value=value)
        
        member_cls: typing.Type[cls] = type(
            name, (cls,), ns
        )
        
        # TODO: Constructor with validation?
        
        member_cls.__qualname__ = f"{cls.__qualname__}.{name}"
        member_cls.__module__ = cls.__module__
        
        member_cls = dataclasses.dataclass(
            member_cls,
            frozen=True  # TODO: ?
        )
        
        members[name] = member_cls
        setattr(cls, name, member_cls)
    
    cls.__annotations__ = {k: v for k, v in cls.__annotations__.items() if k not in members}
    cls._members_ = members
    
    return cls


# def match(union: typing.Type[T], branches: typing.Mapping[typing.Type[T], typing.Callable[[typing.Any], typing.Any]]):
#     """
#     Match statement for tagged unions (and other purposes).
#     Allows matching of instances of tagged union members against their type.
#     Can also just be used as a switch-like statement if used with other objects
#     such as `int`. Uses the tagged union member's constructor arguments as the
#     arguments to the matching branch's function.
#     Args:
#         union (object): The object to be matches
#         branches (dict of object: function): A dict of which functions to call
#             under the different matches. `_` can be used for wildcard matching.
#     Returns:
#         object: The result of calling the match's function.
#     """

#     key = union.name if hasattr(union, 'name') else union

#     if key in branches:
#         action = branches[key]
#     else:
#         action = branches[_]

#     args = union.args if hasattr(union, 'args') else tuple()

#     return action(*args)


__all__ = [
    "tagged_union",
    "Self",
    "Unit",
    # "match",
]
