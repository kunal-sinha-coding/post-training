def unique_sublists(lst):
    # Create a dictionary to store the count of each list
    count_dict = {}
    
    # Iterate through each list in the input list
    for sublist in lst:
        # Convert the sublist to a tuple and update the count in the dictionary
        count_dict[tuple(sublist)] = count_dict.get(tuple(sublist), 0) + 1
    
    # Return the dictionary containing the count of each list
    return count_dict