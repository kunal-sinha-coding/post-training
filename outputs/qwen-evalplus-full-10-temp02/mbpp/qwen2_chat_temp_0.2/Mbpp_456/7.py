# Define the function to reverse each string in a given list of string values
def reverse_string_list(string_list):
    # Use list comprehension to reverse each string in the list
    reversed_list = [s[::-1] for s in string_list]
    # Return the reversed list
    return reversed_list
