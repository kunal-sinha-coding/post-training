def count_Substrings(s):
    # Initialize the count of substrings
    count = 0
    # Iterate through the string
    for i in range(len(s)):
        # Iterate through the string again to find the matching substring
        for j in range(i + 1, len(s) + 1):
            # Calculate the sum of digits in the current substring
            sum_of_digits = sum(int(digit) for digit in s[i:j])
            # If the sum of digits equals the length of the substring, increment the count
            if sum_of_digits == len(s[i:j]):
                count += 1
    return count