def removezero_ip(ip):
    # Split the IP address into its components
    components = ip.split('.')
    # Initialize an empty string to store the result
    result = ''
    # Iterate through each component
    for component in components:
        # Check if the component is not '0' and append it to the result
        if component != '0':
            result += component
    # Return the result string
    return result