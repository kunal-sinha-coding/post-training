import re

def extract_values(input_string):
    # Use regular expression to find all occurrences of quoted strings
    # The pattern looks for strings enclosed in double quotes
    # The findall function returns all non-overlapping matches of the pattern
    # The list comprehension converts each match to a string
    return [match.group(0) for match in re.findall(r'"([^"]*)"', input_string)]
