def consecutive_duplicates(lst):
    # Initialize an empty list to store unique elements
    unique_lst = []
    # Iterate through each element in the input list
    for element in lst:
        # Check if the current element is not the same as the last element in the unique list
        if element != unique_lst[-1]:
            # If not, add the element to the unique list
            unique_lst.append(element)
    # Return the list of unique elements
    return unique_lst