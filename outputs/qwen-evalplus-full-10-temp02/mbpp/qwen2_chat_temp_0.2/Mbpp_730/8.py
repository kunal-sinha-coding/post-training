def consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the list
    for i in range(len(lst)):
        # Check if the current element is not the same as the previous one
        if lst[i] != lst[i - 1]:
            # If it's not the first element, add it to the result list
            if result:
                result.append(lst[i])
            # Add the current element to the result list
            else:
                result.append(lst[i])
    return result