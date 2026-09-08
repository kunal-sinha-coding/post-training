def insert_element(lst, element):
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input list
    for i in lst:
        # Append the element to the result list
        result.append(element)
        # Append the current element to the result list
        result.append(i)
    # Return the result list
    return result