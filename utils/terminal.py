def none(x, none_as='None'):
    return none_as if x is None else x


def and_type(x):
    return x, type(x)


def and_print(x):
    print(x)
    return x


def call(x):
    return x() if callable(x) else x