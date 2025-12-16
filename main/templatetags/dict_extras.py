from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """
    Template filter to lookup dictionary values by key
    Usage: {{ dict|lookup:key }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key, [])
    return []

@register.filter
def get_item(dictionary, key):
    """
    Alternative filter name for dictionary lookup
    Usage: {{ dict|get_item:key }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key, [])
    return []
