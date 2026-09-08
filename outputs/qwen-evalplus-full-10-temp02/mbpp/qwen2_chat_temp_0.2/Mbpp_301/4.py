def dict_depth(d):
    # Initialize the depth to 0
    depth = 0
    # Iterate through each key-value pair in the dictionary
    for key, value in d.items():
        # If the value is a dictionary, recursively calculate the depth
        if isinstance(value, dict):
            depth = max(depth, dict_depth(value))
    # Return the maximum depth found
    return depth