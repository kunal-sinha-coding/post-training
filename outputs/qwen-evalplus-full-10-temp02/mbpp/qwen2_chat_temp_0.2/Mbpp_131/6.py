def reverse_vowels(s):
    """
    Reverse only the vowels of a given string (where y is not a vowel).
    
    Args:
    s (str): The input string to process.
    
    Returns:
    str: The string with vowels reversed.
    """
    vowels = "aeiouAEIOU"
    # Initialize an empty list to store vowels
    vowel_list = []
    # Iterate through each character in the string
    for char in s:
        # Check if the character is a vowel
        if char in vowels:
            # Append the vowel to the vowel_list
            vowel_list.append(char)
    # Join the vowel_list into a string and reverse it
    return ''.join(vowel_list[::-1])
