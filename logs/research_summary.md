# When2Call Research Summary

Current status: Active.

The repository contains When2Call classifiers based on Jina embeddings, MiniLM artifacts, Jev predictions, and rule based ensembles. Several historical experiments report official test accuracy and macro F1. The code also uses test labels to select routing rules and checkpoints. Those results are useful for diagnosis, but they are not valid evidence for clean model selection.

The clean protocol will split `train_pref` deterministically into training and development data. Training labels remain inferred from response content. Development labels are withheld from training and used only for validation. The official test set will remain untouched until the final frozen candidate.

The first experiment is a cheap baseline audit. It will measure class balance, label inference coverage, duplicate source identifiers, and the current checkpoint on the clean development split. The next comparison will test cross entropy against pairwise training under the same split.

Main known risks are noisy inferred training labels, train and evaluation target mismatch, class imbalance, long context truncation, and historical test leakage.
