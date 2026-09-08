def reverse_string_list(string_list):
    # Initialize an empty list to store the reversed strings
    reversed_list = []
    # Iterate over each string in the input list
    for string in string_list:
        # Reverse the string using slicing
        reversed_string = string[::-1]
        # Append the reversed string to the reversed_list
        reversed_list.append(reversed_string)
    # Return the list of reversed strings
    return reversed_list