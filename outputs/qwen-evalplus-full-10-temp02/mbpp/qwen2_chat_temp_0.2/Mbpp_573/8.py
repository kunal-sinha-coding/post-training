def unique_product(numbers):
    # Convert the list to a set to remove duplicates
    unique_numbers = set(numbers)
    # Calculate the product of the unique numbers
    product = 1
    for number in unique_numbers:
        product *= number
    return product