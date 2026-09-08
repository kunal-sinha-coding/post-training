def dif_Square(n):
    # Check if the number is even
    if n % 2 == 0:
        return False
    # Check if the number is odd
    else:
        # Check if the number minus 1 is a perfect square
        if int(n - 1)**2 == n:
            return True
        # Check if the number minus 2 is a perfect square
        elif int(n - 2)**2 == n:
            return True
        # If none of the above conditions are met, the number cannot be represented as the difference of two squares
        return False