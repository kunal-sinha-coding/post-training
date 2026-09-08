def wind_chill(v, t):
    # Calculate the wind chill index using the formula: 35.74 + 0.6215 * v - 35.75 * t
    return round(35.74 + 0.6215 * v - 35.75 * t)