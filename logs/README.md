# Training Logs

Training and evaluation runs append to `logs/logs.txt`. The directory is created automatically when the first log entry is written, and the text log is intentionally ignored by Git because it contains generated run data.

Each run begins with a timestamped header:

```text
------------------------------------------------------------------------
RUN STARTING
Timestamp: 2026-01-01 12:34:56 PST
------------------------------------------------------------------------
```

During training, entries are appended in this order:

1. `Training Step N/T` identifies the current step and total steps.
2. One or more `Generated code:` blocks contain the extracted candidate code; malformed responses include a `Format error:` line.
3. A `Training metrics:` block contains the trainer metrics as indented JSON.

Evaluation entries contain the evaluation name, task ID, prompt, generated code, a `Code execution result:` JSON object, and the numeric `Award`. Evaluation names identify baseline, checkpoint, final, or other evaluation passes.

The configured `log_path` in `configs/default.yaml` and `configs/debug.yaml` controls the destination. Evaluation and training helpers create the parent directory and append to the file rather than replacing earlier runs.
