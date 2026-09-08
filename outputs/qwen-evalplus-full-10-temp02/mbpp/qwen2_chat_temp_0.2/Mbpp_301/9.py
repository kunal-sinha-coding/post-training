def dict_depth(d):
    # Initialize the depth to 0
    depth = 0
    # Iterate through each key-value pair in the dictionary
    for key, value in d.items():
        # If the value is a dictionary, increment the depth
        if isinstance(value, dict):
            depth += 1
        # If the value is not a dictionary, increment the depth by 1
        else:
            depth += 1
    # Return the total depth of the dictionary
    return depth