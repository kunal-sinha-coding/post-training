def consecutive_duplicates(lst):
    # Initialize an empty list to store unique elements
    unique_lst = []
    # Iterate through the list
    for num in lst:
        # Check if the current number is not the first element in the list
        if num != unique_lst[-1]:
            # Add the current number to the unique list
            unique_lst.append(num)
    # Return the list of unique elements
    return unique_lst