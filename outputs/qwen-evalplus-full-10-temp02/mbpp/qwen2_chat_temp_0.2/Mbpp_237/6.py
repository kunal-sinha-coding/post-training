def check_occurences(tuples_list):
    # Create an empty dictionary to store the count of each tuple
    count_dict = {}
    
    # Iterate through each tuple in the list
    for tup in tuples_list:
        # If the tuple is already in the dictionary, increment its count
        if tup in count_dict:
            count_dict[tup] += 1
        # If the tuple is not in the dictionary, add it with a count of 1
        else:
            count_dict[tup] = 1
    
    # Return the dictionary containing the count of each tuple
    return count_dict