def get_ludic(n):
    # Initialize an empty list to store lucid numbers
    lucid_numbers = []
    
    # Iterate through numbers from 1 to n
    for i in range(1, n + 1):
        # Check if the number is a lucid number
        if is_lucid(i):
            # Append the lucid number to the list
            lucid_numbers.append(i)
    
    # Return the list of lucid numbers
    return lucid_numbers
