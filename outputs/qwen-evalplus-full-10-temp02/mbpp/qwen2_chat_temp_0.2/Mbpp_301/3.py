def dict_depth(d):
    # Initialize the depth to 0
    depth = 0
    # Iterate through each key-value pair in the dictionary
    for key, value in d.items():
        # Increment the depth for each level of nesting
        depth += 1
        # Recursively call the function for the value if it's a dictionary
        if isinstance(value, dict):
            depth = dict_depth(value)
    # Return the total depth of the dictionary
    return depth