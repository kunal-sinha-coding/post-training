def text_match_wordz_middle(text):
    # Check if the string contains 'z' except at the start and end
    if text[1:-1] != 'z':
        return True
    else:
        return False