def index_minimum(tuples_list):
    # Initialize variables to store the minimum second value and its index
    min_second = float('inf')
    min_index = -1
    
    # Iterate through each tuple in the list
    for index, (name, value) in enumerate(tuples_list):
        # Check if the current second value is smaller than the minimum second value found so far
        if value < min_second:
            # Update the minimum second value and its index
            min_second = value
            min_index = index
    
    # Return the name of the tuple with the smallest second value
    return tuples_list[min_index][0]