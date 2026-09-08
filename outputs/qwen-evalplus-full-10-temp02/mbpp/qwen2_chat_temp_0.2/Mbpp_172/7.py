def count_occurance(text):
    # Initialize a counter for the substring 'std'
    count = 0
    # Loop through the string to find all occurrences of 'std'
    for i in range(len(text)):
        if text[i:i+3] == 'std':
            count += 1
    # Return the total count of 'std'
    return count