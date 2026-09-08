def count_Substrings(s):
    # Initialize a counter for substrings with the sum of digits equal to their length
    count = 0
    # Iterate through each character in the string
    for i in range(len(s)):
        # Calculate the sum of digits for the current substring
        digit_sum = sum(int(digit) for digit in s[i:])
        # Check if the sum of digits equals the length of the substring
        if digit_sum == len(s[i:]):
            # Increment the counter if the condition is met
            count += 1
    return count
