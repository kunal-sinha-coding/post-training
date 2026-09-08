from collections import Counter

def extract_freq(lst):
    # Count the frequency of each tuple in the list
    freq = Counter(lst)
    # Return the number of unique tuples
    return len(freq)
