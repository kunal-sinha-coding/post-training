def remove_parenthesis(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input list
    for item in lst:
        # Check if the element is not a parenthesis
        if item != '(' and item != ')':
            # Append the element to the result list
            result.append(item)
    # Join the elements in the result list into a single string
    return ''.join(result)