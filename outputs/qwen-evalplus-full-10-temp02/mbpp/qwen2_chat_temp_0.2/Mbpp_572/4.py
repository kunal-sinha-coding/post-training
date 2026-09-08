def two_unique_nums(lists):
    # Use a set to store unique numbers
    unique_numbers = set()
    # Iterate through each list in the input
    for lst in lists:
        # Add each number to the set
        unique_numbers.update(lst)
    # Convert the set back to a list and return it
    return list(unique_numbers)