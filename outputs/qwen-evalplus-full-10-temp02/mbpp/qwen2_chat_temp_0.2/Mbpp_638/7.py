def wind_chill(v, t):
    """
    Calculate the wind chill index rounded to the next integer given the wind velocity in km/h and a temperature in celsius.
    
    Parameters:
    v (float): Wind velocity in km/h.
    t (float): Temperature in celsius.
    
    Returns:
    int: Wind chill index rounded to the next integer.
    """
    # Calculate the wind chill using the formula: W = 35.74 + 0.6215 * T - 35.75 * v**0.16
    w = 35.74 + 0.6215 * t - 35.75 * v**0.16
    # Round the result to the nearest integer
    return round(w)