def check_occurences(tuples_list):
    # Create an empty dictionary to store the count of each tuple
    count_dict = {}
    
    # Iterate through each tuple in the list
    for tuple_ in tuples_list:
        # If the tuple is already in the dictionary, increment its count
        if tuple_ in count_dict:
            count_dict[tuple_] += 1
        # If the tuple is not in the dictionary, add it with a count of 1
        else:
            count_dict[tuple_] = 1
    
    # Return the dictionary containing the count of each tuple
    return count_dict