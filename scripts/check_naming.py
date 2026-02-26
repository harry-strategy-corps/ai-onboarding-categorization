import csv
import json
import re
from collections import Counter

def extract_json(text):
    if not text or not isinstance(text, str): return None
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0).replace('```json', '').replace('```', '').strip()
        try: return json.loads(json_str)
        except:
            try: return json.loads(re.sub(r',\s*\}', '}', json_str))
            except: return None
    return None

def analyze_naming_issues():
    results_path = "data/analysis/04_transaction_categorization_test.csv"
    gt_path = "taxonomy/data/ground_truth_normalized.csv"
    
    gt_data = {}
    with open(gt_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['TRANCD'] not in gt_data: gt_data[row['TRANCD']] = []
            gt_data[row['TRANCD']].append(row)

    issues = Counter()
    
    with open(results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            llm_json = extract_json(row['llm_raw'])
            if not llm_json: continue
            
            trancd = row['TRANCD']
            if trancd not in gt_data: continue
            
            # Find best match (ignoring case)
            matched = False
            for gt_row in gt_data[trancd]:
                if not gt_row['L1']: continue
                
                # Check for specific L3 mismatch
                if str(llm_json.get('category_3', '')).lower().strip() == "internal transfer / payment" and \
                   gt_row['L3'].lower().strip() == "transfers & payments":
                    issues['Internal Transfer / Payment -> Transfers & Payments'] += 1
                
                # Check for case sensitivity issues
                if str(llm_json.get('category_1', '')).strip() == "Non-fee item" and \
                   gt_row['L1'].strip() == "Non-fee item":
                    pass # Match!
                elif str(llm_json.get('category_1', '')).strip().lower() == gt_row['L1'].strip().lower():
                    issues[f"Case mismatch L1: '{llm_json.get('category_1')}' vs '{gt_row['L1']}'"] += 1

    print("\n--- NAMING ALIGNMENT ISSUES ---")
    for issue, count in issues.most_common():
        print(f"{issue}: {count}")

if __name__ == "__main__":
    analyze_naming_issues()
