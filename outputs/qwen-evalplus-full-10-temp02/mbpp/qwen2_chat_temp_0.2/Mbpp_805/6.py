def max_sum_list(lists):
    # Initialize the maximum sum to a very small number
    max_sum = float('-inf')
    # Initialize an empty list to store the result
    result = []
    # Iterate through each sublist in the input list
    for sublist in lists:
        # Calculate the sum of the elements in the current sublist
        current_sum = sum(sublist)
        # Check if the current sum is greater than the maximum sum found so far
        if current_sum > max_sum:
            # Update the maximum sum and store the current sublist
            max_sum = current_sum
            result = [sublist]
        elif current_sum == max_sum:
            # If the current sum is equal to the maximum sum, append the current sublist to the result list
            result.append(sublist)
    # Return the result list containing all sublists with the maximum sum
    return result