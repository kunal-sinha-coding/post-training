def wind_chill(v, t):
    # Calculate the wind chill index using the formula: 
    # W = 35.74 + 0.6215 * T - 35.75 * (v**0.16)
    # Round the result to the nearest integer
    return round(35.74 + 0.6215 * t - 35.75 * (v ** 0.16))