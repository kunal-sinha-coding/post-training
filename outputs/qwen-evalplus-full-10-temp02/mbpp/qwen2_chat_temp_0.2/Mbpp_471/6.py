def find_remainder(arr, n):
    # Initialize the product to 1 (since 1 is the multiplicative identity)
    product = 1
    # Iterate through each element in the array
    for num in arr:
        # Multiply the current product by the current element
        product = (product * num) % n
    # Return the final product
    return product