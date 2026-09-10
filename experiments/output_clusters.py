"""Capture candidate outputs and analyze answer-independent behavioral clusters.

Prepare code and input snapshots for tasks with mixed saved correctness labels.
Run each exact saved solution in a bounded child, stream per-input observations,
then construct clusters and consensus scores before joining benchmark labels.
Persist complete observations, task summaries, hashes, and aggregate measurements.
"""
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import platform
import runpy
import subprocess
import sys
import tempfile
import time

ROOT = Path('outputs/qwen-evalplus-full-10-temp02')
OUT = ROOT / 'output-clusters-v2'
DESERIALIZE = runpy.run_path(str(Path(__file__).with_name('mbpp_input_types.py')))['mbpp_deserialize_inputs']
DATA = Path('qwen_eval/eval_plus/MbppPlus-v0.1.0.jsonl')
EVAL = ROOT / 'mbpp/qwen2_chat_temp_0.2/eval_results.json'

# Hash exact bytes for reproducible source and candidate identity.
def digest(value):
    return hashlib.sha256(value).hexdigest()

# Serialize values with type tags and deterministic mapping and set ordering.
def encode(value):
    kind = type(value).__name__
    if value is None or type(value) in (bool, int, str):
        return [kind, value]
    if type(value) is float:
        return [kind, value.hex()]
    if type(value) in (list, tuple):
        return [kind, [encode(x) for x in value]]
    if type(value) in (set, frozenset):
        return [kind, sorted([encode(x) for x in value], key=repr)]
    if type(value) is dict:
        return [kind, sorted([[encode(k), encode(v)] for k, v in value.items()], key=repr)]
    raise TypeError('Unsupported output type: ' + kind)

# Raise a deadline exception independently of candidate exception classes.
def alarm(signum, frame):
    raise TimeoutError('Probe deadline exceeded.')

# Execute fresh candidate globals for each input and persist each observation immediately.
def child():
    import contextlib
    import copy
    import resource
    import signal
    job = json.load(sys.stdin)
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024**2, 16 * 1024**2))
    signal.signal(signal.SIGALRM, alarm)
    with open(os.devnull, 'w') as sink:
        for suite in ('base_input', 'plus_input'):
            for index, args in enumerate(DESERIALIZE(job['task_id'], job[suite])):
                # Skip observations already persisted by an earlier bounded child.
                if [suite, index] in job.get('skip', []):
                    continue
                row = {'suite': suite, 'index': index}
                signal.setitimer(signal.ITIMER_REAL, 1.0)
                try:
                    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                        scope = {'__name__': 'candidate'}
                        exec(job['code'], scope)
                        value = scope[job['entry_point']](*copy.deepcopy(args))
                        row['status'] = 'returned'
                        try:
                            serialized = json.dumps(encode(value), ensure_ascii=True, separators=(',', ':'))
                            row['value_hash'] = digest(serialized.encode())
                            row['value'] = serialized[:4096]
                            row['truncated'] = len(serialized) > 4096
                        except Exception as exc:
                            row['serialization_error'] = type(exc).__name__
                except BaseException as exc:
                    row['status'] = type(exc).__name__
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                print(json.dumps(row), flush=True)

# Capture a single candidate in a temporary directory with a sanitized environment.
def capture(job):
    destination = OUT / 'observations' / (job['task_id'].replace('/', '_') + '_' + str(job['candidate_index']) + '.json')
    previous = []
    if destination.exists():
        saved = json.loads(destination.read_text())
        assert saved['code_sha256'] == job['code_sha256']
        if len(saved['tests']) == saved['expected_tests']:
            return saved
        previous = saved['tests']
    job = {**job, 'skip': [[x['suite'], x['index']] for x in previous]}
    with tempfile.TemporaryDirectory(prefix='output-cluster-') as directory:
        with open(Path(directory) / 'stream.jsonl', 'w+') as stream:
            process = subprocess.Popen([sys.executable, '-I', str(Path(__file__).resolve()), '--child'], stdin=subprocess.PIPE, stdout=stream, stderr=subprocess.DEVNULL, cwd=directory, env={'PATH': os.environ.get('PATH', ''), 'PYTHONHASHSEED': '0', 'OPENBLAS_NUM_THREADS': '1'})
            timed_out = False
            try:
                process.communicate(json.dumps(job).encode(), timeout=30)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.communicate()
            stream.seek(0)
            observations = []
            for line in stream:
                try:
                    observations.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    record = {k: job[k] for k in ('task_id', 'candidate_index', 'code_sha256')}
    record.update(tests=previous + observations, process_timeout=timed_out, returncode=process.returncode, expected_tests=len(job['base_input']) + len(job['plus_input']))
    destination.write_text(json.dumps(record) + '\n')
    if len(record['tests']) < record['expected_tests'] and observations:
        return capture(job)
    return record

# Construct heuristic pools from observed outputs without benchmark labels.
def pools(records):
    vectors = [{(x['suite'], x['index']): x.get('value_hash') for x in r['tests']} for r in records]
    valid = [i for i, r in enumerate(records) if len(r['tests']) == r['expected_tests'] and all(x.get('value_hash') for x in r['tests'])]
    groups = collections.defaultdict(list)
    for i in valid:
        signature = tuple(sorted(vectors[i].items()))
        groups[signature].append(i)
    clusters = sorted(groups.values(), key=lambda xs: (-len(xs), xs))
    largest = [xs for xs in clusters if len(xs) == len(clusters[0])] if clusters else []
    votes = collections.defaultdict(collections.Counter)
    for i in valid:
        for key, value in vectors[i].items():
            votes[key][value] += 1
    scores = {i: sum(votes[key][value] for key, value in vectors[i].items()) / records[i]['expected_tests'] for i in valid}
    best = [i for i in valid if scores[i] == max(scores.values())] if valid else []
    return {'valid': valid, 'clusters': clusters, 'largest': largest, 'consensus_best': best, 'scores': scores}

# Join correctness only after heuristic pools and clusters have been fixed.
def analyze(records, evaluations, jobs):
    grouped = collections.defaultdict(list)
    for record in records:
        grouped[record['task_id']].append(record)
    tasks = {}
    for task_id, rs in grouped.items():
        rs.sort(key=lambda r: r['candidate_index'])
        selection = pools(rs)
        correct = [r['base_status'] == r['plus_status'] == 'pass' for r in evaluations[task_id]]
        base_correct = [r['base_status'] == 'pass' for r in evaluations[task_id]]
        assert all(r['code_sha256'] == digest(evaluations[task_id][i]['solution'].encode()) for i, r in enumerate(rs))
        rates = {}
        for benchmark, labels in [('base', base_correct), ('combined', correct)]:
            valid = selection['valid'] or list(range(10))
            clusters = selection['largest'] or [list(range(10))]
            best = selection['consensus_best'] or list(range(10))
            rates[benchmark] = {'uniform': sum(labels)/10, 'runtime_uniform': sum(labels[i] for i in valid)/len(valid), 'largest_cluster': sum(sum(labels[i] for i in xs)/len(xs) for xs in clusters)/len(clusters), 'consensus': sum(labels[i] for i in best)/len(best)}
        tasks[task_id] = {**selection, 'correct': correct, 'base_correct': base_correct, 'rates': rates, 'cluster_correct_counts': [sum(correct[i] for i in xs) for xs in selection['clusters']], 'all_ten_return': len(selection['valid']) == 10}
    aggregates = {}
    for benchmark in ('base', 'combined'):
        for subset in ('mixed', 'mixed_all_ten_return'):
            selected = [x for x in tasks.values() if 0 < sum(x['base_correct' if benchmark == 'base' else 'correct']) < 10 and (subset == 'mixed' or x['all_ten_return'])]
            aggregates[benchmark + '_' + subset] = {'tasks': len(selected), **{method: sum(t['rates'][benchmark][method] for t in selected)/len(selected) if selected else None for method in ('uniform', 'runtime_uniform', 'largest_cluster', 'consensus')}}
    mixed = [t for t in tasks.values() if 0 < sum(t['correct']) < 10]
    cluster_stats = {'mixed_tasks': len(mixed), 'tasks_with_clusters': sum(bool(t['clusters']) for t in mixed), 'all_ten_return': sum(t['all_ten_return'] for t in mixed), 'unique_largest_pure_correct': sum(len(t['largest']) == 1 and all(t['correct'][i] for i in t['largest'][0]) for t in mixed), 'unique_largest_pure_incorrect': sum(len(t['largest']) == 1 and not any(t['correct'][i] for i in t['largest'][0]) for t in mixed), 'tied_largest': sum(len(t['largest']) > 1 for t in mixed), 'mixed_label_clusters': sum(any(0 < sum(t['correct'][i] for i in xs) < len(xs) for xs in t['clusters']) for t in mixed)}
    result = {'aggregates': aggregates, 'cluster_stats': cluster_stats, 'tasks': tasks}
    (OUT / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

# Snapshot selected inputs and code, capture outputs concurrently, and save reproducible results.
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'observations').mkdir(exist_ok=True)
    evaluations = json.loads(EVAL.read_text())['eval']
    dataset = {x['task_id']: x for x in map(json.loads, DATA.open())}
    jobs = []
    for task_id, rows in evaluations.items():
        counts = [sum(r['base_status'] == 'pass' for r in rows), sum(r['base_status'] == r['plus_status'] == 'pass' for r in rows)]
        if not any(0 < count < 10 for count in counts):
            continue
        task = dataset[task_id]
        for index, row in enumerate(rows):
            jobs.append({'task_id': task_id, 'candidate_index': index, 'code': row['solution'], 'code_sha256': digest(row['solution'].encode()), **{k: task[k] for k in ('entry_point', 'base_input', 'plus_input')}})
    (OUT / 'jobs.jsonl').write_text(''.join(json.dumps(j) + '\n' for j in jobs))
    metadata = {'python': sys.version, 'platform': platform.platform(), 'workers': 8, 'per_test_timeout_seconds': 1, 'per_candidate_timeout_seconds': 30, 'memory_limit_mb': 512, 'fresh_namespace_per_test': True, 'input_protocol': 'Upstream EvalPlus MBPP input type restoration applied before passing positional arguments. No reference code, assertions, expected outputs, or contract execution.', 'normalization': 'Exact typed values, ordered lists/tuples, sorted dicts and sets, exact float hexadecimal encoding. Unsupported serialization excluded from full-output clusters.', 'tie_policy': 'Exact expected accuracy under uniform choice of tied largest clusters, then uniform member. Consensus ties uniform among candidates. Empty pools fall back to all ten.', 'diagnostic_only': 'Tasks selected by mixed saved labels. Heuristics fixed without labels. Subset accuracy is not full benchmark performance.', 'deserializer_sha256': digest(Path(__file__).with_name('mbpp_input_types.py').read_bytes()), 'data_sha256': digest(DATA.read_bytes()), 'evaluation_sha256': digest(EVAL.read_bytes()), 'script_sha256': digest(Path(__file__).read_bytes()), 'commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()}
    (OUT / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(capture, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            records.append(future.result())
            if len(records) % 100 == 0:
                print(f'Captured {len(records)}/{len(jobs)} candidates.', flush=True)
    result = analyze(records, evaluations, jobs)
    print(json.dumps({k: result[k] for k in ('aggregates', 'cluster_stats')}, indent=2), flush=True)

# Dispatch child execution independently from parent analysis and labels.
if __name__ == '__main__':
    child() if '--child' in sys.argv else main()
