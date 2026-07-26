# Repository Instructions

## Style guidelines

- Favor simplicity over complexity. Do the minimal possible code changes required to achieve the objective.
- Leave inline comments on every function and block of code. Each comment should use complete sentences, but should be as short and simple as possible to communicate the idea. All inline comments must be between 1-2 sentences.

## Git workflow

- After making any set of changes to the code, always commit the changes directly on the `main` branch and push `main` to the repository.

## Command error handling

- Whenever a command such as training or evaluation returns an error, stop and diagnose the error.
- If the fix is simple and straightforward, implement it and rerun the command.
- If there are multiple possible fixes requiring a design decision, or the fix is more than a few lines of code, stop and ask the user for explicit input with one or more options before proceeding.
