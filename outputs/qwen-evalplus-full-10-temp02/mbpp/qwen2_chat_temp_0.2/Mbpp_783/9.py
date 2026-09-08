def rgb_to_hsv(r, g, b):
    """
    Convert rgb color to hsv color.
    
    Args:
    r (int): Red component of the color.
    g (int): Green component of the color.
    b (int): Blue component of the color.
    
    Returns:
    tuple: A tuple representing the hue, saturation, and value of the color.
    """
    # Convert rgb to hsv
    h = 0
    s = 0
    v = 100
    
    # Calculate hue
    if r == g == b:
        h = 0
    elif r == g:
        h = (g + b) / 2
    elif r == b:
        h = (g + r) / 2
    
    # Calculate saturation
    if r == g == b:
        s = 0
    elif r > g:
        s = (r - g) / (r - b)
    elif g > b:
        s = (g - b) / (g - r)
    elif b > r:
        s = (b - r) / (b - g)
    
    # Calculate value
    if r == g == b:
        v = 0
    else:
        v = (r * 255 + g * 255 + b * 255) / 3
    
    return h, s, v
