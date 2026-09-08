# Define the function to extract specified size of strings from a given list of string values
def extract_string(string_list, size):
    # Use list comprehension to extract strings from the list with the specified size
    return [string for string in string_list if len(string) == size]
