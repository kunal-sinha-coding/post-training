def move_num(s):
    # Split the string into a list of characters
    char_list = list(s)
    # Initialize pointers for the start and end of the list
    start = 0
    end = len(char_list) - 1
    # Traverse the list from both ends towards the center
    while start < end:
        # If the current character is a digit, move it to the end
        if char_list[start].isdigit():
            char_list[end] = char_list[start]
            end -= 1
        # If the current character is not a digit, move it to the start
        else:
            char_list[start] = char_list[end]
            start += 1
    # Join the list back into a string and return it
    return ''.join(char_list)