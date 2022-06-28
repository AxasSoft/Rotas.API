def _to_camel_case(s):
    components = s.split('_')
    if len(components) == 1:
        return s
    new_components = [components[0]]
    new_components.extend(el.capitalize() for el in components[1:])
    return ''.join(new_components)


def to_camel_case(data):
    if isinstance(data, list):
        return [to_camel_case(el) for el in data]
    if isinstance(data, dict):
        return {_to_camel_case(k): to_camel_case(v) for k, v in data.items()}
    return data
