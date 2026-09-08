def reverse_vowels(s):
    # Define vowels
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
    reversed_string = ''.join(vowel_list[::-1])
    return reversed_string
