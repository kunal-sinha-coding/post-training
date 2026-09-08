def get_ludic(n):
    # Initialize an empty list to store lucid numbers
    lucid_numbers = []
    # Iterate through numbers starting from 1
    for i in range(1, n + 1):
        # Check if the number is lucid
        if is_lucid(i):
            # Append the number to the lucid_numbers list
            lucid_numbers.append(i)
    # Return the list of lucid numbers
    return lucid_numbers
