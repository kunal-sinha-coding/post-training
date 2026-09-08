def sort_numeric_strings(string_list):
    # Convert each string to an integer, sort them, and then convert them back to strings
    sorted_list = sorted([int(num) for num in string_list])
    return sorted_list