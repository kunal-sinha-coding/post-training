def move_num(s):
    # Split the string into a list of characters
    char_list = list(s)
    # Initialize a variable to track the index of the first non-digit character
    index = 0
    # Iterate through the list of characters
    for i in range(len(char_list)):
        # Check if the character is a digit
        if char_list[i].isdigit():
            # Move the non-digit character to the end of the list
            char_list.insert(index, char_list.pop(i))
            # Increment the index
            index += 1
    # Join the list back into a string and return it
    return ''.join(char_list)