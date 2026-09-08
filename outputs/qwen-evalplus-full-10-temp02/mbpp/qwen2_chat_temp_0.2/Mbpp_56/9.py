def check(n):
    # Convert the number to a string to reverse it
    reversed_n = str(n)[::-1]
    # Check if the number is one less than twice its reverse
    return (n - 2 * int(reversed_n)) == 0