def max_val(heterogeneous_list):
    # Initialize the maximum value with the first element of the list
    max_value = heterogeneous_list[0]
    
    # Iterate through each element in the list
    for element in heterogeneous_list:
        # Update the maximum value if the current element is greater
        if element > max_value:
            max_value = element
    
    # Return the maximum value found
    return max_value