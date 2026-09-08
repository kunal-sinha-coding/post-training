def check_Consecutive(lst):
    # Check if the list is empty
    if not lst:
        return False
    
    # Iterate through the list and check if each element is consecutive
    for i in range(1, len(lst)):
        if lst[i] != lst[i - 1] + 1:
            return False
    
    return True