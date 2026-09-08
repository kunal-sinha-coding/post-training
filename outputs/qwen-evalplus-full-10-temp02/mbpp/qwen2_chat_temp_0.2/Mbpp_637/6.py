def noprofit_noloss(amount, cost):
    # Calculate the profit by subtracting the cost from the amount
    profit = amount - cost
    # Check if the profit is zero or negative
    if profit == 0 or profit < 0:
        return True
    else:
        return False