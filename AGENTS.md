# Repository Instructions

## Style guidelines

- Favor simplicity over complexity. Do the minimal possible code changes required to achieve the objective.
- Leave inline comments on every function and block of code. Each comment should use complete sentences, but should be as short and simple as possible to communicate the idea. All inline comments must be between 1-2 sentences.

## Parallelization

- For tasks with multiple steps, first identify which steps are independent and can run in parallel and which steps depend on one another and must run sequentially.
- Run independent work in parallel with subagents whenever available, then integrate and verify their results before continuing with dependent steps.
- Coordinate edits to shared files to avoid conflicts.

## Git workflow

- After making any set of changes to the code, always commit the changes directly on the `main` branch and push `main` to the repository.

## Patch workflow

- In this environment, the direct patch helper may fail because its sandbox cannot create an unprivileged user namespace. Apply patches through an elevated `exec_command` invocation instead.
- When passing a patch through a nested shell, protect `$` variables, backticks, and quotes from shell interpolation. Base64-encode the patch and pipe it through `base64 -d | apply_patch` when necessary.
