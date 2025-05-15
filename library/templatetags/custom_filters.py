# In your_app_name/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value. Handles potential errors."""
    try:
        # Convert both value and arg to floats or integers if possible
        value = float(value)
        arg = float(arg)
        return value - arg
    except (ValueError, TypeError):
        # Return an empty string or a default value if conversion fails
        return '' # Or return 0, or raise a more specific error