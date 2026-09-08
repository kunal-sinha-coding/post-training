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
    
    if r == g == b:
        h = 0
        s = 100
        v = 100
    elif r == g:
        h = (g - b) / (r - b) * 180
        s = 100
        v = 100
    elif r == b:
        h = (b - g) / (r - g) * 180
        s = 100
        v = 100
    elif g == b:
        h = (b - r) / (g - r) * 180
        s = 100
        v = 100
    
    # Normalize the values
    if v == 0:
        h = 0
    elif v == 100:
        h = 360
    else:
        h = (h * 60) % 360
    
    return h, s, v
