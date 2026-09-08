def move_num(s):
    # Split the string into a list of characters
    char_list = list(s)
    # Initialize a counter for the index
    index = 0
    # Iterate over the list
    for i in range(len(char_list)):
        # If the character is a digit, move it to the end of the list
        if char_list[i].isdigit():
            char_list.insert(index, char_list.pop(i))
            index += 1
    # Join the list back into a string
    return ''.join(char_list)
