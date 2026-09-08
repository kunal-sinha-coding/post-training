def unique_sublists(lst):
    # Dictionary to store the count of each sublist
    count_dict = {}
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Convert the sublist to a tuple and get its count in the original list
        count_dict[sublist] = lst.count(sublist)
    
    # Return the dictionary containing the count of each sublist
    return count_dict