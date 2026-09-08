def index_minimum(tuples_list):
    # Initialize the minimum value with a large number
    min_value = float('inf')
    # Initialize the index of the minimum value with -1
    min_index = -1
    
    # Iterate through each tuple in the list
    for index, (name, score) in enumerate(tuples_list):
        # Check if the current tuple's second value is smaller than the current minimum value
        if score < min_value:
            # Update the minimum value and the index of the minimum value
            min_value = score
            min_index = index
    
    # Return the name of the tuple with the smallest second value
    return tuples_list[min_index][0]