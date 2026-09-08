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
    # Calculate the maximum and minimum values of the RGB components
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    
    # Calculate the difference between the maximum and minimum values
    diff = max_val - min_val
    
    # Calculate the H value
    if diff == 0:
        H = 0
    else:
        H = (60 * (diff / max_val)) % 360
    
    # Calculate the S value
    if max_val == 0:
        S = 0
    else:
        S = (diff / max_val) * 100
    
    # Calculate the V value
    V = max_val
    
    # Return the HSV color as a tuple
    return (H, S, V)