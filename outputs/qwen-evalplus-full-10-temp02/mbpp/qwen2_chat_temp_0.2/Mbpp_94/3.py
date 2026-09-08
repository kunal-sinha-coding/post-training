def index_minimum(tuples_list):
    # Initialize the minimum value with a large number
    min_value = float('inf')
    # Initialize the index of the tuple with the smallest value
    min_index = -1
    
    # Iterate through each tuple in the list
    for index, (name, value) in enumerate(tuples_list):
        # Check if the current tuple's second value is smaller than the current minimum value
        if value < min_value:
            # Update the minimum value and the index of the tuple with the smallest value
            min_value = value
            min_index = index
    
    # Return the name of the tuple with the smallest second value
    return tuples_list[min_index][0]