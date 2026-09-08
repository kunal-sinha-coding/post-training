def remove_Occ(str1, char):
    # Remove the first occurrence of the character
    str1 = str1.replace(char, "")
    # Remove the last occurrence of the character
    str1 = str1.replace(char, "")
    return str1
