def snake_to_camel(snake_str):
    # Split the string by underscores and capitalize the first letter of each word
    camel_str = ''.join(word.capitalize() for word in snake_str.split('_'))
    return camel_str
