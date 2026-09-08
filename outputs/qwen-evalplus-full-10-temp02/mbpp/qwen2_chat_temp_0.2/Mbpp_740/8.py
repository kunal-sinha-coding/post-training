def tuple_to_dict(input_tuple):
    # Initialize an empty dictionary to store the key-value pairs
    result_dict = {}
    # Iterate over the input tuple using a for loop
    for i in range(0, len(input_tuple), 2):
        # Assign the adjacent elements to the key and value in the dictionary
        result_dict[input_tuple[i]] = input_tuple[i+1]
    # Return the dictionary containing the key-value pairs
    return result_dict