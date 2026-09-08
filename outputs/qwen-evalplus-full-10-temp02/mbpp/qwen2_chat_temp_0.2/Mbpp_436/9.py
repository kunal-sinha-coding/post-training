def neg_nos(lst):
    """
    This function takes a list of numbers as input and returns a new list containing only the negative numbers from the input list.
    
    Parameters:
    lst (list): A list of numbers.
    
    Returns:
    list: A list containing only the negative numbers from the input list.
    """
    # Initialize an empty list to store negative numbers
    neg_list = []
    # Iterate through each number in the input list
    for num in lst:
        # Check if the number is negative
        if num < 0:
            # Append the negative number to the neg_list
            neg_list.append(num)
    # Return the list of negative numbers
    return neg_list