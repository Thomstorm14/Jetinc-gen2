import json

path = r'F:\JETinc\JETcity_Launchpad\jetinc_build\benchmark_results.json'

with open(path, 'r') as f:
    data = json.load(f)

def verdict_to_score(rough_text):
    """
    Reads the real grader's verdict out of the _ROUGH field instead of
    hardcoding a label. Returns 'CORRECT' or 'INCORRECT' based on what
    the grader actually said.
    """
    if not rough_text:
        return 'UNSCORED'
    text = rough_text.strip().upper()
    if text.startswith('CORRECT'):
        return 'CORRECT'
    if text.startswith('INCORRECT'):
        return 'INCORRECT'
    # Fallback: search for the words anywhere if it didn't start clean
    if 'INCORRECT' in text:
        return 'INCORRECT'
    if 'CORRECT' in text:
        return 'CORRECT'
    return 'UNSCORED'

def check_for_error(answer_text):
    """Flags timeouts/errors so they never get scored as CORRECT."""
    if not answer_text:
        return True
    return answer_text.strip().startswith('[ERROR')

for item in data:
    baseline_rough = item.get('baseline_auto_score_ROUGH', '')
    deliberated_rough = item.get('deliberated_auto_score_ROUGH', '')

    baseline_answer = item.get('baseline_answer', '')
    deliberated_answer = item.get('deliberated_answer', '')

    # Real score, pulled from the actual grader verdict
    item['baseline_score'] = verdict_to_score(baseline_rough)
    item['deliberated_score'] = verdict_to_score(deliberated_rough)

    # Any answer that's actually an error/timeout is forced to INCORRECT,
    # no matter what the grader text says
    if check_for_error(baseline_answer):
        item['baseline_score'] = 'ERROR'
    if check_for_error(deliberated_answer):
        item['deliberated_score'] = 'ERROR'

    # Hallucination flag: derived from the real correctness call.
    # An answer that's INCORRECT or ERROR relative to ground truth counts
    # as a hallucination for this benchmark's purposes.
    item['baseline_hallucinated'] = 'YES' if item['baseline_score'] in ('INCORRECT', 'ERROR') else 'NO'
    item['deliberated_hallucinated'] = 'YES' if item['deliberated_score'] in ('INCORRECT', 'ERROR') else 'NO'

with open(path, 'w') as f:
    json.dump(data, f, indent=4)

# Print an honest summary instead of a canned success message
total = len(data)
b_correct = sum(1 for i in data if i['baseline_score'] == 'CORRECT')
d_correct = sum(1 for i in data if i['deliberated_score'] == 'CORRECT')
b_halluc = sum(1 for i in data if i['baseline_hallucinated'] == 'YES')
d_halluc = sum(1 for i in data if i['deliberated_hallucinated'] == 'YES')

print('=== REAL SCORING COMPLETE (no hardcoded labels) ===')
print(f'Total tasks: {total}')
print(f'Baseline correct: {b_correct}/{total} | Deliberated correct: {d_correct}/{total}')
print(f'Baseline hallucinated: {b_halluc}/{total} | Deliberated hallucinated: {d_halluc}/{total}')
print('These numbers came from the actual grader verdict field, not a fixed value.')
