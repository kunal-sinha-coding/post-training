def rgb_to_hsv(r, g, b):
    """
    Convert RGB color to HSV color.
    
    Parameters:
    r (int): Red component of the color.
    g (int): Green component of the color.
    b (int): Blue component of the color.
    
    Returns:
    tuple: A tuple representing the HSV color in the format (h, s, v).
    """
    # Convert RGB to HSL
    h = 0
    s = 0
    v = 100
    
    # Calculate H
    if r == g == b:
        h = 0
    elif r == g:
        h = (g - b) / (r - b) * 180
    elif r == b:
        h = (b - g) / (r - g) * 180
    
    # Calculate S
    if r == g == b:
        s = 0
    else:
        s = (max(r, g, b) - min(r, g, b)) / (max(r, g, b) - min(r, g, b))
    
    # Calculate V
    if r == g == b:
        v = 0
    else:
        v = max(r, g, b)
    
    return h, s, v