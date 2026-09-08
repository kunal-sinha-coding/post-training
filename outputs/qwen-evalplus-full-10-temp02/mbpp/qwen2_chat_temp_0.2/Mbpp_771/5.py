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
            # Check if the stack is empty
            if not stack:
                return False
            # Pop the top element from the stack
            stack.pop()
    
    # If the stack is empty, all opening parentheses had matching closing ones
    return len(stack) == 0