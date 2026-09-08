def armstrong_number(num):
    # Convert the number to a string to easily iterate over each digit
    num_str = str(num)
    # Calculate the sum of each digit raised to the power of the number of digits
    sum_of_powers = sum(int(digit) ** len(num_str) for digit in num_str)
    # Check if the sum of powers is equal to the original number
    return sum_of_powers == num
