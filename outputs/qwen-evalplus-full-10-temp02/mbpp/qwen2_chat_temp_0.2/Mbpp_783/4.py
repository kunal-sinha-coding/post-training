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
    # Calculate the maximum and minimum values
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    
    # Calculate the difference between max and min values
    diff = max_val - min_val
    
    # Calculate the hue
    if max_val == min_val:
        hue = 0
    else:
        hue = (60 * (diff / max_val)) % 360
    
    # Calculate the saturation
    if max_val == 0:
        saturation = 0
    else:
        saturation = (diff / max_val) * 100
    
    # Calculate the value
    value = max_val
    
    # Return the hue, saturation, and value as a tuple
    return (hue, saturation, value)