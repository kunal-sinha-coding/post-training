def is_polite(n):
    # Initialize the first polite number as 1
    polite_number = 1
    # Initialize the count of polite numbers found
    count = 0
    
    # Loop until the count reaches n
    while count < n:
        # Check if the current polite number is even
        if polite_number % 2 == 0:
            # If it is, increment the count
            count += 1
        # Increment the polite number by 2
        polite_number += 2
    
    # Return the nth polite number
    return polite_number