def insert_element(lst, element):
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input list
    for i in lst:
        # Append the current element to the result list
        result.append(element)
        # Append the current element to the result list again to maintain the order
        result.append(element)
    # Return the resulting list
    return result