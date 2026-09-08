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
    h = (r + g + b) / 360.0
    s = 1.0 - max(r, g, b)
    v = min(r, g, b)
    
    # Normalize h and s
    if s == 0:
        h = 0
    else:
        h = (h + 180) / 360.0
    
    return h, s, v