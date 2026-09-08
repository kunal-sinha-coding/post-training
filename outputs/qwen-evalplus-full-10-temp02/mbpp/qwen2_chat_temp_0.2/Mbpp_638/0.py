def wind_chill(wind_velocity, temperature):
    """
    Calculate the wind chill index rounded to the next integer given the wind velocity in km/h and a temperature in celsius.
    
    Parameters:
    wind_velocity (float): The wind velocity in km/h.
    temperature (float): The temperature in celsius.
    
    Returns:
    int: The wind chill index rounded to the next integer.
    """
    # Calculate the wind chill using the formula: 35.71 * (1.618 * T - 0.427 * V)
    wind_chill_index = round(35.71 * (1.618 * temperature - 0.427 * wind_velocity))
    return wind_chill_index