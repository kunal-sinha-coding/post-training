def check_Consecutive(lst):
    # Check if the list is empty or has only one element
    if len(lst) <= 1:
        return False
    
    # Iterate through the list starting from the second element
    for i in range(1, len(lst)):
        # Check if the current element is not equal to the next element
        if lst[i] != lst[i - 1]:
            return False
    
    # If all elements are consecutive, return True
    return True