def count_Occurrence(lst, tuple):
    # Initialize a dictionary to store the count of each element in the tuple
    count_dict = {}
    
    # Iterate over each element in the tuple
    for element in tuple:
        # If the element is already in the dictionary, increment its count
        if element in count_dict:
            count_dict[element] += 1
        # If the element is not in the dictionary, add it with a count of 1
        else:
            count_dict[element] = 1
    
    # Return the total count of all elements in the tuple
    return sum(count_dict.values())
