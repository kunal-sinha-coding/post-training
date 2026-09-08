# Define the function to extract specified size of strings from a given list of string values
def extract_string(string_list, size):
    # Use list comprehension to extract the specified size of strings
    result = [string_list[i:i+size] for i in range(0, len(string_list), size)]
    return result
