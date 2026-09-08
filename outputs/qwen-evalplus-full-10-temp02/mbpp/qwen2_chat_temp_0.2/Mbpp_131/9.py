def reverse_vowels(s):
    # Define vowels
    vowels = "aeiouAEIOU"
    # Initialize an empty string to store the result
    result = ""
    # Iterate over each character in the input string
    for char in s:
        # Check if the character is a vowel
        if char in vowels:
            # Append the vowel to the result string in reverse order
            result = char + result
        else:
            # Append the character as is to the result string
            result = result + char
    return result