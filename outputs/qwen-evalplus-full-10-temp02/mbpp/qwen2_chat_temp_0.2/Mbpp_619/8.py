def move_num(s):
    # Split the string into a list of characters
    char_list = list(s)
    # Initialize two pointers, one at the start and one at the end of the list
    left = 0
    right = len(char_list) - 1
    # Traverse the list
    while left < right:
        # Move the left pointer to the right until it finds a non-digit character
        while left < right and not char_list[left].isdigit():
            left += 1
        # Move the right pointer to the left until it finds a digit character
        while left < right and char_list[right].isdigit():
            right -= 1
        # Swap the characters at the left and right pointers
        char_list[left], char_list[right] = char_list[right], char_list[left]
    # Join the list back into a string and return it
    return ''.join(char_list)
