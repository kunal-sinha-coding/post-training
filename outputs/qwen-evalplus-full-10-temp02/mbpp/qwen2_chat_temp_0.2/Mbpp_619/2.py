def move_num(s):
    # Split the string into a list of characters
    chars = list(s)
    # Initialize a pointer for the end of the list
    end = len(chars) - 1
    # Iterate through the list from the end to the beginning
    for i in range(len(chars) - 1, -1, -1):
        # If the character is a number, move it to the end
        if chars[i].isdigit():
            chars.insert(end, chars.pop(i))
            end -= 1
    # Join the list back into a string
    return ''.join(chars)