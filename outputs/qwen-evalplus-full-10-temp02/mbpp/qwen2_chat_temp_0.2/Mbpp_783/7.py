def rgb_to_hsv(r, g, b):
    # Convert RGB to HSV
    h = 0
    s = 0
    v = 0
    
    # Calculate the maximum and minimum values
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    
    # Calculate the difference between max and min
    diff = max_val - min_val
    
    # Calculate the saturation
    if diff == 0:
        s = 0
    else:
        s = diff / max_val
    
    # Calculate the value
    v = max_val
    
    # Calculate the hue
    if r == g == b:
        h = 0
    elif r == g:
        h = (g - b) / (max_val - min_val)
    elif r == b:
        h = (b - g) / (max_val - min_val)
    else:
        h = (g - r) / (max_val - min_val)
    
    # Return the HSV color
    return h, s, v