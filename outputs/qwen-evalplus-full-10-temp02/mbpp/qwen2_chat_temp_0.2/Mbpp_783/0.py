def rgb_to_hsv(r, g, b):
    # Convert RGB to HSL
    h = (r + g + b) / 360
    s = max(r, g, b) / 255
    v = min(r, g, b) / 255
    return h, s, v