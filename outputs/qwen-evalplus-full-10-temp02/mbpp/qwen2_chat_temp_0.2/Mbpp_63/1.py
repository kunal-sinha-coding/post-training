def max_difference(tup_list):
    # Sort the list of tuples based on the second element of each tuple
    sorted_tup_list = sorted(tup_list, key=lambda x: x[1])
    # Initialize the maximum difference to a very small number
    max_diff = float('-inf')
    # Iterate through the sorted list to find the maximum difference
    for i in range(len(sorted_tup_list) - 1):
        # Calculate the difference between consecutive tuples
        diff = sorted_tup_list[i + 1][0] - sorted_tup_list[i][1]
        # Update the maximum difference if the current difference is greater
        if diff > max_diff:
            max_diff = diff
    return max_diff