def return_sum(dict):
    # Initialize sum to 0
    total_sum = 0
    # Iterate through each key-value pair in the dictionary
    for key, value in dict.items():
        # Add the value to the total sum
        total_sum += value
    # Return the total sum
    return total_sum