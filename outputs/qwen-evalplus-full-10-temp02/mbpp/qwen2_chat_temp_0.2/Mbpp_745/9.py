def divisible_by_digits(startnum, endnum):
    # Define a lambda function to check divisibility by each digit
    def check_divisibility_by_digit(num):
        # Convert the number to a string to iterate over each digit
        num_str = str(num)
        # Iterate over each character in the string
        for digit in num_str:
            # Check if the digit is divisible by the current number
            if num % int(digit) != 0:
                return False
        return True
    
    # Use list comprehension to filter numbers within the range that are divisible by every digit
    return [num for num in range(startnum, endnum + 1) if check_divisibility_by_digit(num)]
