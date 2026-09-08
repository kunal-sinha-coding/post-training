def max_sum_list(lists):
    # Initialize variables to keep track of the maximum sum and the corresponding list
    max_sum = float('-inf')
    max_list = []
    
    # Iterate through each list in the input list
    for sublist in lists:
        # Calculate the sum of elements in the current sublist
        current_sum = sum(sublist)
        
        # Check if the current sum is greater than the maximum sum found so far
        if current_sum > max_sum:
            # Update the maximum sum and the corresponding list
            max_sum = current_sum
            max_list = sublist
    
    # Return the list of lists with the maximum sum
    return max_list