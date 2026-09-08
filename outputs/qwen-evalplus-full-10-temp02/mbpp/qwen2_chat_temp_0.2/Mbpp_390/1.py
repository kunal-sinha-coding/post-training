def add_string(lst, format_string):
    # Iterate over each element in the list
    for i in lst:
        # Replace the placeholder '{0}' with the current element
        lst[i] = format_string.format(i)
    # Return the modified list
    return lst