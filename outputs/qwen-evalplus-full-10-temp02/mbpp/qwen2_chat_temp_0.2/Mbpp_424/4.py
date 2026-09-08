def extract_rear(string_tuple):
    # Initialize an empty list to store the rear indices of each string
    rear_indices = []
    # Iterate over each string in the tuple
    for string in string_tuple:
        # Extract the last character of the string
        rear_index = string[-1]
        # Append the rear index to the list
        rear_indices.append(rear_index)
    # Return the list of rear indices
    return rear_indices
