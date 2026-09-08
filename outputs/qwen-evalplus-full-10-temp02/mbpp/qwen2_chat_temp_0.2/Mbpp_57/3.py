def find_Max_Num(digits):
    # Sort the digits in descending order
    digits.sort(reverse=True)
    # Initialize the result to the first digit
    result = digits[0]
    # Iterate through the sorted digits
    for digit in digits[1:]:
        # Multiply the result by 10 and add the current digit
        result *= 10
        result += digit
    return result