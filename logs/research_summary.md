# When2Call research status

The current user direction is to combine the best existing trained encoder approaches and the best existing trained LLM approach. The next comparison reuses Qwen2.5 1.5B SFT and the saved Jina models.

The encoder experts are the best single Jina checkpoint at seed 20261048 and the historical three-Jina ensemble at seeds 20261065, 20261061, and 20261048. The latter preserves raw-logit weights 0.35625, 0.1375, and 0.50625. Each expert is combined with Qwen through equal probability averaging and minimum entropy gating. All four methods are frozen before one shared aggregate-only test pass. The same forward passes produce the three baseline measurements.

No new training or combination fitting is part of this comparison. The old preference partition is not clean validation for the saved encoders because their warm start saw all preference rows. No weights or router will be fitted on those labels. Historical repeated benchmark inspection also limits generalization claims. All new primary macro F1 measurements include four classes. A present-class aggregate diagnostic is reported separately for historical comparisons.

The fresh-encoder detour has been recorded and is outside the requested comparison. Its three pending ensemble tests were removed. The already running validation worker is allowed to exit. The exact active and pending commands are stored in logs/research_state.json. A supervised 30-second watchdog dispatches the pending existing-model commands and returns planning to this Codex thread when the queue is empty.
