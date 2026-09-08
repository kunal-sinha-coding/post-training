def reverse_string_list(string_list):
    # Initialize an empty list to store the reversed strings
    reversed_list = []
    # Iterate over each string in the input list
    for string in string_list:
        # Reverse the string and append it to the reversed_list
        reversed_list.append(string[::-1])
    # Return the list of reversed strings
    return reversed_list