def list_to_float(list_of_lists):
    # Initialize an empty list to store the converted floats
    converted_list = []
    
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Initialize an empty list to store the converted elements
        converted_elements = []
        
        # Iterate over each element in the sublist
        for element in sublist:
            # Convert the element to a float and append it to the converted_elements list
            converted_elements.append(float(element))
        
        # Append the converted elements list to the converted_list
        converted_list.append(converted_elements)
    
    # Return the converted_list
    return converted_list