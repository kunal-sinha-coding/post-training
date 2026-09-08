def dict_depth(d):
    # Initialize the depth to 0
    depth = 0
    # Iterate through each key-value pair in the dictionary
    for key, value in d.items():
        # If the value is a dictionary, recursively calculate the depth
        if isinstance(value, dict):
            # Increment the depth by 1 for each level of nesting
            depth += 1
            # Recursively call the function with the nested dictionary
            depth += dict_depth(value)
    # Return the total depth of the dictionary
    return depth