def diff_even_odd(lst):
    # Initialize variables to store the first even and first odd numbers
    first_even = None
    first_odd = None
    
    # Iterate through the list to find the first even and first odd numbers
    for num in lst:
        if num % 2 == 0:
            if first_even is None:
                first_even = num
            else:
                first_even = min(first_even, num)
        else:
            if first_odd is None:
                first_odd = num
            else:
                first_odd = min(first_odd, num)
    
    # Calculate the difference between the first even and first odd numbers
    return first_even - first_odd