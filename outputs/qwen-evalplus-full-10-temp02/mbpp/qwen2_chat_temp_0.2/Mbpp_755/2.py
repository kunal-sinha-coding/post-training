def second_smallest(numbers):
    # Convert the list to a set to remove duplicates and sort it
    unique_sorted_numbers = sorted(set(numbers))
    # Check if there are at least two unique numbers
    if len(unique_sorted_numbers) < 2:
        return None  # Return None if there are not enough unique numbers
    # Return the second smallest number
    return unique_sorted_numbers[1]
