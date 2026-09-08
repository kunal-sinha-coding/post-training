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
        h = (g - b) / 255 * 180
    elif r == b:
        h = (b - g) / 255 * 180
    
    # Calculate saturation
    if r == g == b:
        s = 0
    else:
        s = (max(r, g, b) - min(r, g, b)) / 255
    
    # Calculate value
    v = max(r, g, b)
    
    # Return the hue, saturation, and value as a tuple
    return (h, s, v)