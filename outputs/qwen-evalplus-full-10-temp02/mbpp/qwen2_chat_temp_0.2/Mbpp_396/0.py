def check_char(s):
    # Check if the string starts and ends with the same character
    if s.startswith(s[-1]) and s.endswith(s[0]):
        return "Valid"
    else:
        return "Invalid"