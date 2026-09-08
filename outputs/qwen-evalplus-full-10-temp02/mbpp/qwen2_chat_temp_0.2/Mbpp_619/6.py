def move_num(s):
    # Split the string into a list of characters
    chars = list(s)
    # Initialize pointers for the start and end of the list
    start = 0
    end = len(chars) - 1
    # Move characters to the end of the list
    while start < end:
        # Swap the characters at the start and end pointers
        chars[start], chars[end] = chars[end], chars[start]
        # Move the pointers towards the center
        start += 1
        end -= 1
    # Join the list back into a string and return it
    return ''.join(chars)
