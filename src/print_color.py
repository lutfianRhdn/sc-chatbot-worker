"""
Minimal print-color replacement for testing
"""

def print(*args, **kwargs):
    """Simple print replacement that ignores color arguments"""
    import builtins
    # Filter out color-specific kwargs
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['color', 'background', 'format']}
    builtins.print(*args, **filtered_kwargs)