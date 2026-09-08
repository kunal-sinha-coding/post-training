def max_sum_list(lists):
    # Initialize the maximum sum to a very low value
    max_sum = float('-inf')
    
    # Iterate through each sublist in the list
    for sublist in lists:
        # Calculate the sum of the elements in the current sublist
        current_sum = sum(sublist)
        
        # Check if the current sum is greater than the maximum sum found so far
        if current_sum > max_sum:
            # Update the maximum sum if the current sum is greater
            max_sum = current_sum
    
    # Return the list of sublists whose sum is the highest
    return max_sum_list