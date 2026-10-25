# When2Call research status

The October 25 restart prioritizes a heterogeneous ensemble. The members are the existing Qwen RPO 0.5B adapter, existing Qwen SFT 1.5B adapter, and a fresh upstream Jina encoder.

The encoder uses the exact 7,200-row Qwen training partition. The shared validation excludes 214 questions present in training and contains 1,586 rows. Question groups stay together in the stacker fitting and selection halves. The initial methods are equal probability blending, minimum entropy gating, and a fixed regularized linear stacker.

The old encoder is excluded from clean validation because its warm start saw all preference rows. Saved Qwen adapters retain their learned label index order despite the historical prompt mismatch. All new primary macro F1 scores include four classes. Historical encoder scores often excluded absent classes and cannot be compared directly.

The old best observed aggregate accuracy was 0.678806 from Qwen SFT 1.5B. The old best observed ensemble macro F1 was 0.592015 under a different metric convention and a repeated test comparison protocol. These remain historical references. No new ensemble result is available yet.

The six exact commands and live process are stored in logs/research_state.json. The first worker trains the fresh encoder. It is followed by standalone testing, ensemble selection, and one aggregate measurement per frozen method. A supervised watchdog checks every 30 seconds and returns planning to the current Codex thread when the queue is empty.
