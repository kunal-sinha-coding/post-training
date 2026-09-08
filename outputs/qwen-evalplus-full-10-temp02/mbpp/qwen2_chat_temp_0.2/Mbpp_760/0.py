def unique_Element(numbers):
    # Convert the list to a set to remove duplicates
    unique_numbers = set(numbers)
    # Check if the length of the set is 1, which means all numbers were unique
    return len(unique_numbers) == 1