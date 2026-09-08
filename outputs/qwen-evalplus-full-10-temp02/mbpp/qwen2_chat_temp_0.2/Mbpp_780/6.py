def find_combinations(tup_list):
    # Initialize an empty list to store the combinations
    result = []
    # Iterate through each tuple in the input list
    for tup in tup_list:
        # Iterate through each element in the tuple
        for i in range(len(tup)):
            # Iterate through each element in the tuple
            for j in range(i + 1, len(tup)):
                # Calculate the sum of the current tuple and the next tuple
                sum_of_tuples = tup[i] + tup[j]
                # Append the tuple to the result list if the sum is less than or equal to 10
                if sum_of_tuples <= 10:
                    result.append(tup)
    return result