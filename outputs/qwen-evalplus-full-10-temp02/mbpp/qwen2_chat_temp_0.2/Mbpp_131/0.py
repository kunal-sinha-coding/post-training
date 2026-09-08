def reverse_vowels(s):
    # Define vowels
    vowels = "aeiouAEIOU"
    # Initialize an empty string to store the result
    result = ""
    # Iterate through each character in the input string
    for char in s:
        # Check if the character is a vowel
        if char in vowels:
            # Append the vowel to the result string
            result += char
        else:
            # Append the non-vowel character to the result string
            result += char
    # Return the result string with vowels reversed
    return result