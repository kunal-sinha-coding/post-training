def snake_to_camel(snake_str):
    # Split the string by underscores to get the words
    words = snake_str.split('_')
    # Capitalize the first letter of each word and join them together
    camel_case_str = words[0].upper() + ''.join(word.capitalize() for word in words[1:])
    return camel_case_str
