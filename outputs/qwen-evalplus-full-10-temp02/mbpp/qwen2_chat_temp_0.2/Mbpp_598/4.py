def armstrong_number(n):
    # Convert the number to a string to easily iterate over each digit
    str_n = str(n)
    # Calculate the sum of the cubes of each digit
    sum_of_cubes = sum(int(digit) ** 3 for digit in str_n)
    # Check if the sum of cubes is equal to the original number
    return sum_of_cubes == n