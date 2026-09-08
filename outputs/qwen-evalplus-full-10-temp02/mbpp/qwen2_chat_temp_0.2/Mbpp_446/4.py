def count_Occurrence(list1, list2):
    # Initialize a dictionary to store the count of each element in list1
    count_dict = {}
    
    # Iterate over each element in list1
    for element in list1:
        # If the element is already in the dictionary, increment its count
        if element in count_dict:
            count_dict[element] += 1
        # If the element is not in the dictionary, add it with a count of 1
        else:
            count_dict[element] = 1
    
    # Initialize a counter for the total count of elements in list2
    total_count = 0
    
    # Iterate over each element in list2
    for element in list2:
        # If the element is in the dictionary, add its count to the total count
        if element in count_dict:
            total_count += count_dict[element]
        # If the element is not in the dictionary, add it with a count of 0
        else:
            total_count += 0
    
    # Return the total count of elements in list2
    return total_count