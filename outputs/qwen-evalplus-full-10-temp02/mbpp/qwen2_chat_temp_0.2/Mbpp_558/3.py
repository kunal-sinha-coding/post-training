def digit_distance_nums(num1, num2):
    # Calculate the absolute difference between the two numbers
    diff = abs(num1 - num2)
    # Calculate the sum of the digits of the difference
    sum_diff = sum(int(digit) for digit in str(diff))
    return sum_diff