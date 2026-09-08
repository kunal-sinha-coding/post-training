def reverse_vowels(s):
    # Define vowels
    vowels = "aeiouAEIOU"
    # Initialize an empty list to store vowels
    vowels_list = []
    # Iterate through each character in the string
    for char in s:
        # Check if the character is a vowel
        if char in vowels:
            # Add the vowel to the vowels_list
            vowels_list.append(char)
    # Join the vowels_list into a string and reverse it
    reversed_string = ''.join(vowels_list)[::-1]
    return reversed_string