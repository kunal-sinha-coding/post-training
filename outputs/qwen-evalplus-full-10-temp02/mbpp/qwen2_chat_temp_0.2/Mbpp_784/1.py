def mul_even_odd(numbers):
    # Initialize product to 1 (since 1 is the multiplicative identity)
    product = 1
    # Flag to check if there is at least one even number
    has_even = False
    # Flag to check if there is at least one odd number
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
    
    # If there was at least one even number, return the product
    if has_even:
        return product
    # If there was at least one odd number, return the product
    elif has_odd:
        return product
    # If neither even nor odd number was found, return 0
    else:
        return 0