# Define a function to filter odd numbers from a given list
def filter_oddnumbers(numbers):
    # Use list comprehension to filter out odd numbers
    odd_numbers = [num for num in numbers if num % 2 != 0]
    # Return the list of odd numbers
    return odd_numbers
