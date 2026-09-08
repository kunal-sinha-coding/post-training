def check_expression(expression):
    # Initialize a stack to keep track of opening parentheses
    stack = []
    
    # Iterate through each character in the expression
    for char in expression:
        # If the character is an opening parenthesis, push it onto the stack
        if char == '(':
            stack.append(char)
        # If the character is a closing parenthesis
        elif char == ')':
            # If the stack is empty, it means there's no matching opening parenthesis
            if not stack:
                return False
            # Pop the top of the stack, which should be an opening parenthesis
            stack.pop()
    
    # If the stack is empty, all opening parentheses had matching closing ones
    return len(stack) == 0