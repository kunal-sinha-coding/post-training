def check_Consecutive(lst):
    # Check if the list is empty or has only one element
    if len(lst) <= 1:
        return False
    
    # Iterate through the list and check for consecutive numbers
    for i in range(1, len(lst)):
        if lst[i] == lst[i - 1] + 1:
            continue
        else:
            return False
    
    return True