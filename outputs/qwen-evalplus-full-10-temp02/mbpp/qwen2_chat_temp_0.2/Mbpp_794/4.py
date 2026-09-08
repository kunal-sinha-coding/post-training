import re

def text_starta_endb(text):
    # Define the pattern to match 'a' followed by any character, ending with 'b'
    pattern = 'a.*b'
    # Use re.search to find the pattern in the text
    if re.search(pattern, text):
        return True
    else:
        return False
