def check_Consecutive(lst):
    # Check if the list is empty
    if not lst:
        return False
    
    # Iterate through the list and check for consecutive numbers
    for i in range(len(lst) - 1):
        if lst[i] + 1 == lst[i + 1]:
            return True
    
    # If no consecutive numbers are found, return False
    return False