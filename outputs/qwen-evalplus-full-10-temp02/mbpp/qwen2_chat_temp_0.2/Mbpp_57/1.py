def find_Max_Num(digits):
    # Sort the digits in descending order
    digits.sort(reverse=True)
    # Initialize the result with the first digit
    result = digits[0]
    # Iterate through the sorted digits and multiply them to form the result
    for digit in digits[1:]:
        result *= digit
    return result
