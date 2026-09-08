def move_num(s):
    # Split the string into a list of characters
    char_list = list(s)
    # Initialize pointers for the start and end of the list
    start = 0
    end = len(char_list) - 1
    
    # Move characters to the end of the list
    while start < end:
        # Swap the characters at the start and end pointers
        char_list[start], char_list[end] = char_list[end], char_list[start]
        # Move the pointers towards the center
        start += 1
        end -= 1
    
    # Join the list back into a string
    return ''.join(char_list)
