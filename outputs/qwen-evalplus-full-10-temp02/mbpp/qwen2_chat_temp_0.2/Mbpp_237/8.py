def check_occurences(tuples_list):
    # Create an empty dictionary to store the occurrences of each tuple
    occurrences = {}
    
    # Iterate through each tuple in the list
    for tuple in tuples_list:
        # If the tuple is already in the dictionary, increment its count
        if tuple in occurrences:
            occurrences[tuple] += 1
        # If the tuple is not in the dictionary, add it with a count of 1
        else:
            occurrences[tuple] = 1
    
    # Return the dictionary containing the occurrences of each tuple
    return occurrences