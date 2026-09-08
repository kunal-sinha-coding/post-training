# Define the function to convert tuple string to integer tuple
def tuple_str_int(tup_str):
    # Convert the string to a tuple using the tuple() constructor
    return tuple(int(num) for num in tup_str.split(','))
