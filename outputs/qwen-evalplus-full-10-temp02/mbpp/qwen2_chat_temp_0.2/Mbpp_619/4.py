def move_num(s):
    # Split the string into a list of words
    words = s.split()
    # Initialize an empty list to store the numbers
    num_list = []
    # Iterate through each word in the list
    for word in words:
        # Check if the word is a number
        if word.isdigit():
            # Append the number to the num_list
            num_list.append(word)
    # Join the num_list back into a string with spaces
    result = ' '.join(num_list)
    return result