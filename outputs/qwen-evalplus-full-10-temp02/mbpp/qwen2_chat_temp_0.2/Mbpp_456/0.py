def reverse_string_list(string_list):
    # Iterate over each string in the list
    for i in range(len(string_list)):
        # Reverse the string using slicing
        string_list[i] = string_list[i][::-1]
    # Return the modified list
    return string_list