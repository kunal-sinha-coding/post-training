def is_product_even(numbers):
    # Initialize the product to 1 (since multiplying by 1 does not change the product)
    product = 1
    # Flag to check if the product is even
    is_even = True
    
    # Iterate through each number in the list
    for num in numbers:
        # Multiply the current number with the product
        product *= num
        # Check if the product is even
        if product % 2 != 0:
            is_even = False
    
    # Return True if the product is even, otherwise False
    return is_even