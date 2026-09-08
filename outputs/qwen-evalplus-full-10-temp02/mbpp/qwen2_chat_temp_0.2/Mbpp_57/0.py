def find_Max_Num(digits):
    # Sort the digits in descending order
    digits.sort(reverse=True)
    # Initialize the result to the first digit
    result = digits[0]
    # Iterate through the sorted digits to find the largest number
    for digit in digits:
        result = max(result, digit)
    return result