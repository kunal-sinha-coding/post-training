def list_to_float(list_of_lists):
    # Initialize an empty list to store the converted floats
    converted_floats = []
    
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Initialize an empty list to store the elements of the current sublist
        temp_list = []
        
        # Iterate over each element in the current sublist
        for element in sublist:
            # Convert the element to a float and append it to the temp_list
            temp_list.append(float(element))
        
        # Append the temp_list to the converted_floats list
        converted_floats.append(temp_list)
    
    # Return the list of converted floats
    return converted_floats