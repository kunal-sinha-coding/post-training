def find_tuples(tuples_list, k):
    # Initialize an empty list to store tuples with all elements divisible by k
    divisible_tuples = []
    
    # Iterate through each tuple in the list
    for tup in tuples_list:
        # Check if all elements in the tuple are divisible by k
        if all(x % k == 0 for x in tup):
            # If all elements are divisible, add the tuple to the list
            divisible_tuples.append(tup)
    
    # Return the list of tuples with all elements divisible by k
    return divisible_tuples