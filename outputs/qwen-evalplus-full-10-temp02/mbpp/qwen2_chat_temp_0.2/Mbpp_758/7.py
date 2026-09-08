def unique_sublists(lst):
    # Initialize an empty dictionary to store the count of each sublist
    count_dict = {}
    
    # Iterate through each sublist in the input list
    for sublist in lst:
        # Convert the sublist to a tuple and store it in the dictionary
        count_dict[tuple(sublist)] = count_dict.get(tuple(sublist), 0) + 1
    
    # Return the dictionary containing the count of each sublist
    return count_dict