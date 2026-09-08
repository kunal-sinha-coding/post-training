def extract_string(string_list, size):
    # Use list comprehension to extract the specified size of strings
    return [string for string in string_list if len(string) == size]