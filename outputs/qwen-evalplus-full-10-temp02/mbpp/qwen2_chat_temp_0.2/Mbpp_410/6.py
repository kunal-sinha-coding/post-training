def min_val(heterogeneous_list):
    # Initialize the minimum value with the first element of the list
    min_value = heterogeneous_list[0]
    
    # Iterate through each element in the list
    for element in heterogeneous_list:
        # Update min_value if the current element is smaller
        if element < min_value:
            min_value = element
    
    # Return the minimum value found
    return min_value