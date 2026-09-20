# GRPO reward plateau audit

This audit examines code at commit 6dc5e1f, installed TRL 0.25.0, Transformers 4.56.2, PEFT 0.21.0, Accelerate 1.15.0 and PyTorch 2.8.0+cu126. It replays the 128 real-reward v4 completions and runs three controlled forward/backward checks. It does not restart training or claim a benchmark improvement.

## Evidence and corrections

The 572-task training greedy pass rate changed from 0.629371 to 0.632867 between steps zero and 520. Test fraction changed from 0.687099 to 0.693520. The separate 32-task comparison used the selected step-50 adapter, not step 520. It improved sampled full-pass rate by only 2/512. These show little demonstrated improvement, not established degradation.

W&B MCP sampled histories for cool-fog-74 (dizijcbf) show noisy batch rewards and a small rise in cumulative reward, approximately 0.531 early to 0.548 late in the returned sample. Retrieved metrics include train/reward, train/reward_std, train/frac_reward_zero_std, train/loss, train/learning_rate, train/completions/mean_length, reward/test_progress/mean, reward/full_pass_fraction, training/rolling_average_reward, training/average_reward and reward/flat_group_fraction. Retrieval used 25 and 20 sampled rows, not an exhaustive history. W&B _step is a logging index, not the optimizer step. Flat-group fractions in retrieved rows vary substantially and mean those groups supply no relative reward gradient. Diversity is not globally absent: the earlier repeated-sampling study had only 5/32 flat groups.

## Confirmed training mismatch

In evaluate.py, CodeFenceCriteria returns bool(all(finished)) rather than a per-completion finished vector. One completion can continue past its stopping string while another is still generating. In sandbox.py, reward_function truncates each completion at its own first stop string. TRL masks tokens after EOS, not after this custom stop string. The trained completion can therefore contain an unscored suffix. This includes generated tests and explanations, not merely a closing fence.

In all 128 v4 real-reward traces, 78 (60.94%) have more than 30 characters removed. Retokenizing decoded raw text gives 23,628 tokens versus 12,805 tokens for scored prefixes, a 45.81% difference. This is an approximate text-token comparison, not an exact count of masked training token IDs. Task 627 includes generated assertions and explanatory text discarded by the scorer. These suffixes consume computation and receive the same advantage as the scored code. With token weighting, they can substantially change the gradient. This is a concrete candidate contributor, not proof that it explains the plateau.

The repair must coordinate per-row stopping with loss masks and token-count normalization. Merely returning a finished vector can introduce padding that TRL's EOS-only masking counts. The confirmation test should verify that no padding or content after the first stop contributes to the loss, then compare real-reward training on the same fixed tasks.

## Diagnostic problems

The installed GRPOConfig defaults to loss_type=dapo. Its accumulated objective weights completion tokens. Our probe reports equally weighted mean log probabilities per completion. These measure different directions when lengths vary. DAPO itself is not a bug. The probe should replay the actual frozen-old-policy, token-masked surrogate with the same normalizer and numerical context as training. TRL shuffles tensor fields together, including advantages, and disables Transformers' extra gradient-accumulation scaling via a non-None compute_loss_func. Static inspection found no obvious independent reward shuffle or double accumulation division.

The standalone deterministic experiment bypasses TRL entirely and uses SGD. It cannot rule out a bug in the actual trainer, and the same numerical learning rate has a different effect under SGD and Adam. Individual positive sample likelihood need not increase when a shared-parameter weighted objective improves. Prior claims that these tests proved an optimization failure, or established that the full trainer had a correct loss sign, were too strong.

The probe also used a bfloat16 base model. New precision controls below show that its tiny likelihood changes are strongly precision dependent. A zero-learning-rate rerun produced exactly zero changes, ruling out the suspected gradient-enabled versus no-grad difference alone for this example. At float32 and SGD learning rate 0.001, the loss fell by about 0.0000626, close to the first-order prediction of 0.001 times the squared gradient norm, about 0.0000622. The prior bfloat16 run at the same rate instead showed a loss increase. Thus attributing that result to overshoot or a reversed gradient was not justified. Float32 at 3e-6 produced a positive delta of 3.43e-7 and a negative delta of zero at displayed precision. These checks do not prove bfloat16 training is unusable; they show that the diagnostic cannot resolve small updates reliably in its previous form.

## Other possible contributors

LoRA dropout is configured at 0.05 and disable_dropout is not explicitly set. The installed default is False. This adds stochasticity to optimization and differs from the eval-mode direction probe. Disabling it is a targeted follow-up, not an established explanation.

The real long run used a decaying learning rate and a limited number of examples with a useful within-group reward difference. These can reduce learning, but we have not established that increasing learning rate, rank or group count solves the issue. The synthetic position-based reward cannot improve by construction and is unsuitable for comparing learning curves. Enlarging its batch can average away arbitrary labels rather than create a learnable coding signal.

## Scoring replay and coverage

All 128 stored scored completions were rerun with the original tests, timeout 3 seconds, hybrid reward coefficient 0.5. There were zero reward mismatches. Outcomes were 68 full passes (53.125%), 21 partial passes (16.406%), 38 zero-test passes (29.688%), and 1 syntax failure (0.781%). These exhaustive outcome categories are not claimed as a complete semantic taxonomy. For example, task 627 uses an incorrect arithmetic-sum algorithm for first missing integer, while task 617 contains invalid dp[][] syntax. The replay checks consistency of the existing scorer, not correctness of all dataset tests. There is no evidence here that the reward is accidentally always zero or inverted.

## Prioritized next action

First correct stopping and token masks, and replace the diagnostic with an exact before/after replay of the installed TRL objective. Verify zero-step invariance, gradient/update alignment and loss change with dropout disabled and consistent precision. Then run the same fixed-task real-reward experiment, preserving the optimizer, learning rate and data so the effect of the repair is measurable. Do not conclude that larger LoRA rank or a larger learning rate is required from the current results.

## Reproduction and limitations

Controls use the fixed prompt and completions in experiments/deterministic_grpo_probe.py, seed 42, rank 16, alpha 32 and zero dropout, without benchmark selection. Commands are python experiments/deterministic_grpo_probe.py --learning-rate 0 --output outputs/deterministic-grpo-probe/audit-zero.json and the float32 override scripts reproduced below. No held-out benchmark was evaluated. GPU has approximately 15.58 GiB memory. Previous final vLLM startup failures are separate memory-management failures and do not invalidate already-recorded optimizer metrics. No training implementation was changed in this audit.

### audit-zero.json

```json
{
  "model": "Qwen/Qwen2.5-Coder-3B-Instruct",
  "seed": 42,
  "learning_rate": 0.0,
  "prompt": "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n<|im_start|>user\nWrite a Python function named add(a, b) that returns the sum of a and b.<|im_end|>\n<|im_start|>assistant\n",
  "completions": [
    "```python\ndef add(a, b):\n    return a + b\n```",
    "```python\ndef add(a, b):\n    return a - b\n```"
  ],
  "advantages": [
    0.5,
    -0.5
  ],
  "before_logps": [
    -0.22975651919841766,
    -0.9133500456809998
  ],
  "after_logps": [
    -0.22975651919841766,
    -0.9133500456809998
  ],
  "logp_deltas": [
    0.0,
    0.0
  ],
  "before_loss": -0.17089837789535522,
  "after_loss": -0.17089837789535522,
  "gradient_norm": 0.25241637229919434,
  "positive_direction_passed": false,
  "negative_direction_passed": false
}

```

### audit-fp32.json

```json
{
  "model": "Qwen/Qwen2.5-Coder-3B-Instruct",
  "seed": 42,
  "learning_rate": 3e-06,
  "prompt": "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n<|im_start|>user\nWrite a Python function named add(a, b) that returns the sum of a and b.<|im_end|>\n<|im_start|>assistant\n",
  "completions": [
    "```python\ndef add(a, b):\n    return a + b\n```",
    "```python\ndef add(a, b):\n    return a - b\n```"
  ],
  "advantages": [
    0.5,
    -0.5
  ],
  "before_logps": [
    -0.2333468794822693,
    -0.917169451713562
  ],
  "after_logps": [
    -0.23334653675556183,
    -0.917169451713562
  ],
  "logp_deltas": [
    3.427267074584961e-07,
    0.0
  ],
  "before_loss": -0.17095564305782318,
  "after_loss": -0.17095573246479034,
  "gradient_norm": 0.24945642054080963,
  "positive_direction_passed": true,
  "negative_direction_passed": false
}

```

### audit-fp32-1e-3.json

```json
{
  "model": "Qwen/Qwen2.5-Coder-3B-Instruct",
  "seed": 42,
  "learning_rate": 0.001,
  "prompt": "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n<|im_start|>user\nWrite a Python function named add(a, b) that returns the sum of a and b.<|im_end|>\n<|im_start|>assistant\n",
  "completions": [
    "```python\ndef add(a, b):\n    return a + b\n```",
    "```python\ndef add(a, b):\n    return a - b\n```"
  ],
  "advantages": [
    0.5,
    -0.5
  ],
  "before_logps": [
    -0.2333468794822693,
    -0.917169451713562
  ],
  "after_logps": [
    -0.2333560585975647,
    -0.9174290895462036
  ],
  "logp_deltas": [
    -9.179115295410156e-06,
    -0.00025963783264160156
  ],
  "before_loss": -0.17095564305782318,
  "after_loss": -0.17101825773715973,
  "gradient_norm": 0.24945642054080963,
  "positive_direction_passed": false,
  "negative_direction_passed": true
}

```

### audit-traces.json

```json
{
  "rows": 128,
  "source_sha256": "2c96bc1be5ba7b8e26fdba83445d6fb2f376f3255360029bdb16120f45b1993f",
  "statuses": {
    "partial": 21,
    "passed": 68,
    "failed": 38,
    "syntax_error": 1
  },
  "mismatches": [],
  "raw_tokens": 23628,
  "scored_prefix_tokens": 12805,
  "tails_over_30_chars": 78,
  "examples": [
    {
      "task_id": "627",
      "reward": 0.16666666666666666,
      "tail": "\n# Test cases\nassert find_First_Missing([0, 1, 2, 3], 0, 3) == 4\nassert find_First_Missing([0, 1, 2, 6, 9], 0, 4) == 3\nassert find_First_Missing([2, 3, 5, 8, 9], 0, 4) == 0\n```"
    },
    {
      "task_id": "627",
      "reward": 0.16666666666666666,
      "tail": "\n# Test the function\nassert find_First_Missing([0,1,2,3],0,3) == 4\nassert find_First_Missing([0,1,2,6,9],0,4) == 3\nassert find_First_Missing([2,3,5,8,9],0,4) == 0\n```\n\nThis solution uses a combination of sorting, partitioning, and counting unique elements to find the smallest missing number in an array."
    }
  ],
  "versions": {
    "torch": "2.8.0+cu126",
    "transformers": "4.56.2",
    "trl": "0.25.0",
    "peft": "0.21.0",
    "accelerate": "1.15.0"
  }
}
```

### Reproduction script audit_precision.py

```python
import sys
sys.path.insert(0, '/workspace/post-training')
import torch
from argparse import Namespace
from experiments import deterministic_grpo_probe as p
original = p.AutoModelForCausalLM.from_pretrained

def load(*args, **kwargs):
    kwargs['torch_dtype'] = torch.float32
    return original(*args, **kwargs)
p.AutoModelForCausalLM.from_pretrained = load
torch.backends.cuda.matmul.allow_tf32 = False
p.run_probe(Namespace(model='Qwen/Qwen2.5-Coder-3B-Instruct', seed=42, learning_rate=3e-6, output='outputs/deterministic-grpo-probe/audit-fp32.json'))

```

### Reproduction script audit_precision_large.py

```python
import sys
sys.path.insert(0, '/workspace/post-training')
import torch
from argparse import Namespace
from experiments import deterministic_grpo_probe as p
original = p.AutoModelForCausalLM.from_pretrained

def load(*args, **kwargs):
    kwargs['torch_dtype'] = torch.float32
    return original(*args, **kwargs)
p.AutoModelForCausalLM.from_pretrained = load
torch.backends.cuda.matmul.allow_tf32 = False
p.run_probe(Namespace(model='Qwen/Qwen2.5-Coder-3B-Instruct', seed=42, learning_rate=1e-3, output='outputs/deterministic-grpo-probe/audit-fp32-1e-3.json'))

```

### Reproduction script audit_traces.py

```python
import sys,json,collections,hashlib,importlib.metadata
from pathlib import Path
sys.path.insert(0,'/workspace/post-training')
from transformers import AutoTokenizer
from sandbox import score_completion
p=Path('outputs/grpo-mbpp-reward-direction-probe-g16-v4/reward-trace.jsonl')
rows=[json.loads(x) for x in p.read_text().splitlines()]
t=AutoTokenizer.from_pretrained('Qwen/Qwen2.5-Coder-3B-Instruct')
stats={'rows':len(rows),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'statuses':dict(collections.Counter(r['detail']['status'] for r in rows)),'mismatches':[],'raw_tokens':0,'scored_prefix_tokens':0,'tails_over_30_chars':0,'examples':[],'versions':{k:importlib.metadata.version(k) for k in ['torch','transformers','trl','peft','accelerate']}}
for i,r in enumerate(rows):
 reward,detail=score_completion(r['scored_completion'],r['test_code'],3,'hybrid',.5)
 if reward!=r['reward']: stats['mismatches'].append({'row':i,'old':r['reward'],'new':reward})
 stats['raw_tokens']+=len(t.encode(r['raw_completion'],add_special_tokens=False))
 stats['scored_prefix_tokens']+=len(t.encode(r['truncated_completion'],add_special_tokens=False))
 stats['tails_over_30_chars']+=len(r['raw_completion'])-len(r['truncated_completion'])>30
 if len(stats['examples'])<2 and len(r['raw_completion'])-len(r['truncated_completion'])>150:
  stats['examples'].append({'task_id':r['task_id'],'reward':r['reward'],'tail':r['raw_completion'][len(r['truncated_completion']):][:600]})
Path('outputs/deterministic-grpo-probe/audit-traces.json').write_text(json.dumps(stats,indent=2))
print(json.dumps(stats,indent=2))

```
