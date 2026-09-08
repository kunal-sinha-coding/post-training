def reverse_vowels(s):
    """
    Reverse only the vowels of a given string (where y is not a vowel).
    
    Args:
    s (str): The input string.
    
    Returns:
    str: The string with vowels reversed.
    """
    vowels = "aeiouAEIOU"
    result = []
    for char in s:
        if char in vowels:
            result.append(char)
        else:
            result.append(char)
    return ''.join(result)
