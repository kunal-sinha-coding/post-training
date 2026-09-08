def second_smallest(numbers):
    # Convert the list to a set to remove duplicates
    unique_numbers = set(numbers)
    # Sort the unique numbers in ascending order
    sorted_numbers = sorted(unique_numbers)
    # Return the second smallest number if there are at least two unique numbers
    if len(sorted_numbers) >= 2:
        return sorted_numbers[1]
    else:
        return None  # Return None if there are not enough unique numbers