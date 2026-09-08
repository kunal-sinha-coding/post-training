def reverse_vowels(s):
    # Define a set of vowels for easy lookup
    vowels = set('aeiouAEIOU')
    # Initialize an empty list to store the vowels in reverse order
    vowels_list = []
    # Iterate over each character in the string
    for char in s:
        # Check if the character is a vowel
        if char in vowels:
            # Append the vowel to the list
            vowels_list.append(char)
    # Join the list of vowels in reverse order into a string
    return ''.join(vowels_list[::-1])
