def diff_even_odd(lst):
    # Initialize variables to store the first even and first odd numbers
    first_even = None
    first_odd = None
    
    # Iterate through the list to find the first even and first odd numbers
    for num in lst:
        if num % 2 == 0:
            first_even = num
        elif num % 2 != 0:
            first_odd = num
    
    # Calculate the difference between the first even and first odd numbers
    if first_even is not None and first_odd is not None:
        return first_odd - first_even
    else:
        return None  # Return None if no even or odd numbers are found