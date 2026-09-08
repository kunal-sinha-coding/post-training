def find_combinations(tup_list):
    # Initialize an empty list to store the combinations
    result = []
    # Iterate over each tuple in the input list
    for tup in tup_list:
        # Iterate over each element in the tuple
        for i in range(len(tup)):
            # Iterate over each element in the tuple again
            for j in range(i + 1, len(tup)):
                # Calculate the sum of the current tuple and the current element
                sum_tup = tup[i] + tup[j]
                # Check if the sum is a tuple
                if isinstance(sum_tup, tuple):
                    # Append the tuple to the result list
                    result.append(sum_tup)
    # Return the list of combinations
    return result