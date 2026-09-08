def second_smallest(numbers):
    # Convert the list to a set to remove duplicates
    unique_numbers = set(numbers)
    
    # Check if there are at least two unique numbers
    if len(unique_numbers) < 2:
        return None  # Return None if there are not enough unique numbers
    
    # Convert the set back to a list and sort it
    sorted_unique_numbers = sorted(unique_numbers)
    
    # Return the second smallest number
    return sorted_unique_numbers[1]
