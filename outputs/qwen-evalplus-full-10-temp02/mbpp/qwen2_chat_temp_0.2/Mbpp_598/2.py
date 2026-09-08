def armstrong_number(num):
    # Convert the number to a string to iterate over each digit
    num_str = str(num)
    # Calculate the sum of the cubes of each digit
    sum_of_cubes = sum(int(digit) ** 3 for digit in num_str)
    # Check if the sum of cubes is equal to the original number
    return sum_of_cubes == num