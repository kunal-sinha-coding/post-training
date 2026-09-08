# Define the function to remove words with k length
def remove_length(input_string, k):
    # Split the input string into words
    words = input_string.split()
    # Initialize an empty list to store words with k length
    result = []
    # Iterate over each word in the list
    for word in words:
        # Check if the length of the word is equal to k
        if len(word) == k:
            # If it is, add the word to the result list
            result.append(word)
    # Join the result list into a single string and return it
    return ' '.join(result)
