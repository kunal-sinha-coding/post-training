# Define the function to filter out negative numbers from a list
def neg_nos(numbers):
    # Use list comprehension to filter out negative numbers
    return [num for num in numbers if num < 0]
