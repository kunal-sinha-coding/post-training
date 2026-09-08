def removezero_ip(ip):
    # Split the IP address into its components
    components = ip.split('.')
    # Initialize an empty list to store the components without leading zeroes
    result = []
    # Iterate through each component
    for component in components:
        # Check if the component is not empty and starts with a digit
        if component and component[0].isdigit():
            # Append the component to the result list
            result.append(component)
    # Join the components back into a single string with a dot separator
    return '.'.join(result)