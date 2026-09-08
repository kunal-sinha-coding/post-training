def remove_parenthesis(arr):
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input list
    for i in arr:
        # Check if the element is not a parenthesis
        if i != '(':
            # Append the element to the result list
            result.append(i)
    # Join the elements in the result list into a single string
    return ''.join(result)