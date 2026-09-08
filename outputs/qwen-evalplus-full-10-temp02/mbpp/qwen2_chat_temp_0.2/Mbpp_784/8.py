def mul_even_odd(numbers):
    # Initialize product to 1 (since 1 is the multiplicative identity)
    product = 1
    # Flag to check if there are even numbers
    has_even = False
    # Flag to check if there are odd numbers
    has_odd = False
    
    # Iterate through each number in the list
    for num in numbers:
        # Check if the number is even
        if num % 2 == 0:
            has_even = True
            # Multiply the product by the even number
            product *= num
        # Check if the number is odd
        elif num % 2 != 0:
            has_odd = True
            # Multiply the product by the odd number
            product *= num
    
    # If there were no even or odd numbers, return 0
    if not has_even and not has_odd:
        return 0
    else:
        # Return the product of the first even and odd number
        return product
