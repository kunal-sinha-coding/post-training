def armstrong_number(number):
    # Convert the number to a string to iterate over each digit
    num_str = str(number)
    # Calculate the sum of the cubes of each digit
    sum_of_cubes = sum(int(digit) ** 3 for digit in num_str)
    # Check if the sum of cubes is equal to the original number
    return sum_of_cubes == number