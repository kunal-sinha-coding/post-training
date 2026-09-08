def count_Substrings(s):
    count = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            if sum(int(digit) for digit in s[i:j]) == len(s[i:j]):
                count += 1
    return count