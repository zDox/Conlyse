from enum import EnumMeta


class DefaultEnumMeta(EnumMeta):
    """
    A Metaclass which makes the first entry of an Enum its
    default value
    """
    default = object()

    def __call__(cls, value=default, *args, **kwargs):
        if value is DefaultEnumMeta.default:
            # Assume the first enum is default
            return next(iter(cls))
        return super().__call__(value, *args, **kwargs)

    def get_value_type(cls):
        if len(cls) == 0:
            return None
        else:
            return type(next(iter(cls)).value)
