def sort_numeric_strings(string_list):
    # Convert the list of strings to a list of integers
    integer_list = [int(num) for num in string_list]
    # Sort the list of integers numerically
    integer_list.sort()
    # Convert the sorted list of integers back to a list of strings
    sorted_string_list = [str(num) for num in integer_list]
    return sorted_string_list