def is_polite(n):
    """
    Find nth polite number.
    geeksforgeeks.org/n-th-polite-number/
    """
    # Base case: if n is 1, return 1
    if n == 1:
        return 1
    # Initialize the first polite number
    polite_number = 1
    # Initialize the count of polite numbers found
    count = 0
    
    # Loop to find the nth polite number
    while count < n:
        # Check if the current polite number is a polite number
        if is_polite_number(polite_number):
            count += 1
        # Increment the polite number
        polite_number += 1
    
    # Return the nth polite number
    return polite_number
