# Define the function to check if a substring is present in a list of strings
def find_substring(string_list, substring):
    # Iterate through each string in the list
    for string in string_list:
        # Check if the current string is a substring of the given substring
        if substring in string:
            return True
    # If no substring is found in any string, return False
    return False
