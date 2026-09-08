def remove_length(input_string, k):
    # Split the string into words
    words = input_string.split()
    # Filter out words with length k
    filtered_words = [word for word in words if len(word) != k]
    # Join the filtered words back into a string
    result = ' '.join(filtered_words)
    return result