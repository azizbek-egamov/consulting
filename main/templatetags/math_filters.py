from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Shablonda ikki sonni ayirish uchun filter"""
    try:
        return value - arg
    except (TypeError, ValueError):
        return 0
    
@register.filter
def kopaytir(value, arg):
    return value * arg

@register.filter
def initials_dot(value):
    return ' '.join([word[0].upper() + '.' for word in value.split() if word])