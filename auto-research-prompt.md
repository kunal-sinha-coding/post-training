# Autonomous Research Agent: When2Call Optimization

This file records the user supplied autonomous research prompt for this repository.

## Mission

Build the highest performing When2Call system while maximizing accuracy and macro F1. Continue empirical research until the user sends the exact top level message `STOP`.

## Hard constraints

- Every individual model must have at most 2 billion parameters.
- Do not train on, inspect, or select with test examples or test labels.
- Use a dedicated development or validation split for all experiments and freeze the final system before one authorized official test evaluation.
- Inspect existing reports, logs, code, data processing, labels, checkpoints, and evaluation practice before new experiments.

## Research loop

Continuously analyze the current best validation accuracy and macro F1, formulate one concrete hypothesis, run a reproducible experiment, evaluate accuracy, macro F1, per class metrics, and a confusion matrix, classify every failure, record the result, and select the next experiment. Keep successful and failed experiments, preserve checkpoints, and use small pilots before expensive runs.

Investigate model architecture, training data, label quality, class balance, context construction, loss functions, calibration, ensembles, multi stage inference, error categories, and robustness across seeds. Research external resources only after checking provenance, licensing, and benchmark contamination.

## Evaluation integrity

Use one stable evaluation harness with all classes included in macro F1. Keep candidate selection independent of ground truth. Use execution, observable outputs, resource behavior, or agreement only during selection, then join labels for a separate measurement. Explicitly audit the mismatch between inferred training labels and direct evaluation labels.

## Persistent research state

Maintain a research log, a validation only leaderboard, a current hypothesis, an experiment queue, active process identifiers, checkpoints, reproduction commands, a current summary, and a last successful heartbeat. Record experiment ID, timestamps, hypothesis, setup, dataset, preprocessing, model, parameters, seed, code revision, checkpoint, inference settings, metrics, runtime, analysis, limitations, and next action. Never silently overwrite results.

## Watchdog and recovery

Implement an executable watchdog that checks every five minutes. It must inspect active experiments, agent activity, heartbeat timestamps, process health, crashes, and stalls. It must use durable state and locking to avoid duplicate workers, recover completed or crashed work, and record recovery actions. If independent unattended agent invocation is unavailable, document the strongest feasible supervisor and its limitation.

## Resource and stopping rules

Inspect hardware, reuse caches, avoid uncontrolled disk use, and do not start paid resources without authorization. Continue research after successes, failures, plateaus, crashes, or temporary resource limits. The only permanent stopping condition is an exact top level user message consisting of `STOP`. On that message, stop new experiments, safely checkpoint active work, disable automatic restarts, persist final state, and report the final summary.

## Immediate execution

Inspect the repository and reports. Audit data, labels, evaluation, and leakage. Summarize prior results and bottlenecks. Create the log, leaderboard, state, summary, and watchdog. Build a prioritized roadmap. Launch the first high value validation experiment and continue the research loop.

The complete user prompt is preserved in the conversation that created this file. This repository copy records its operative requirements without changing them.
