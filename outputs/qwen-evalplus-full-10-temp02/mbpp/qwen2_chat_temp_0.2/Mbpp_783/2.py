def rgb_to_hsv(r, g, b):
    """
    Convert RGB color to HSV color.
    
    Args:
    r (int): Red component of the color.
    g (int): Green component of the color.
    b (int): Blue component of the color.
    
    Returns:
    tuple: A tuple representing the HSV color (H, S, V).
    """
    # Convert RGB to HSL
    h = 0
    s = 0
    v = 0
    
    if r == g == b:
        h = 0
        s = 100
        v = 0
    else:
        h = 180 * (255 - max(r, g, b)) / (max(r, g, b) + min(r, g, b))
        s = 100 * (max(r, g, b) - min(r, g, b)) / (max(r, g, b) + min(r, g, b))
        v = min(r, g, b)
    
    return (h, s, v)