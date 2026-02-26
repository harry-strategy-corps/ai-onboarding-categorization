import csv
import json
import re
from collections import defaultdict

def extract_json(text):
    if not text or not isinstance(text, str):
        return None
    # Try to find JSON block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Clean up possible markdown code blocks around JSON
        json_str = json_str.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(json_str)
        except:
            # Try to fix common issues: trailing commas
            try:
                json_str = re.sub(r',\s*\}', '}', json_str)
                return json.loads(json_str)
            except:
                return None
    return None

def analyze_results():
    results_path = "data/analysis/04_transaction_categorization_test.csv"
    gt_path = "taxonomy/data/ground_truth_normalized.csv"
    
    # Load ground truth into a dict of lists (codes can have multiple mappings)
    gt_data = defaultdict(list)
    try:
        with open(gt_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gt_data[row['TRANCD']].append(row)
    except Exception as e:
        print(f"Error reading ground truth: {e}")
        return

    # Load and analyze results
    stats = {
        'total': 0,
        'parsed': 0,
        'exact_match': 0,
        'partial_match': 0, # L1 + L2
        'l1_match': 0,
        'l2_match': 0,
        'l3_match': 0,
        'l4_match': 0,
        'no_gt': 0
    }
    
    failures = []
    
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total'] += 1
                trancd = row['TRANCD']
                llm_json = extract_json(row['llm_raw'])
                
                if not llm_json:
                    continue
                
                stats['parsed'] += 1
                
                cat1 = str(llm_json.get('category_1', '')).strip().lower()
                cat2 = str(llm_json.get('category_2', '')).strip().lower()
                cat3 = str(llm_json.get('category_3', '')).strip().lower()
                cat4 = str(llm_json.get('category_4', '')).strip().lower()
                
                if trancd not in gt_data:
                    stats['no_gt'] += 1
                    continue
                
                # Check if it matches ANY of the valid mappings for this code
                best_match = None
                matched_any_l1 = False
                matched_any_l2 = False
                matched_any_l3 = False
                matched_any_l4 = False
                matched_any_exact = False
                matched_any_partial = False
                
                for gt_row in gt_data[trancd]:
                    # Ignore empty GT rows (Capa 3)
                    if not gt_row['L1']:
                        continue
                        
                    gt_l1 = str(gt_row['L1']).strip().lower()
                    gt_l2 = str(gt_row['L2']).strip().lower()
                    gt_l3 = str(gt_row['L3']).strip().lower()
                    gt_l4 = str(gt_row['L4']).strip().lower()
                    
                    m1 = cat1 == gt_l1
                    m2 = cat2 == gt_l2
                    m3 = cat3 == gt_l3 or (not cat3 and not gt_l3)
                    m4 = cat4 == gt_l4 or (not cat4 and not gt_l4)
                    
                    if m1: matched_any_l1 = True
                    if m2: matched_any_l2 = True
                    if m3: matched_any_l3 = True
                    if m4: matched_any_l4 = True
                    
                    if m1 and m2: matched_any_partial = True
                    if m1 and m2 and m3 and m4:
                        matched_any_exact = True
                        best_match = gt_row
                        break
                
                if matched_any_l1: stats['l1_match'] += 1
                if matched_any_l2: stats['l2_match'] += 1
                if matched_any_l3: stats['l3_match'] += 1
                if matched_any_l4: stats['l4_match'] += 1
                if matched_any_partial: stats['partial_match'] += 1
                if matched_any_exact: stats['exact_match'] += 1
                else:
                    if trancd in gt_data and any(r['L1'] for r in gt_data[trancd]):
                        failures.append({
                            'code': trancd,
                            'desc': row['sample_desc_1'],
                            'actual': f"{llm_json.get('category_1')} > {llm_json.get('category_2')} > {llm_json.get('category_3')} > {llm_json.get('category_4')}",
                            'expected': f"{gt_data[trancd][0]['L1']} > {gt_data[trancd][0]['L2']} > {gt_data[trancd][0]['L3']} > {gt_data[trancd][0]['L4']}"
                        })

    except Exception as e:
        print(f"Error during analysis: {e}")
        return

    print("\n" + "="*40)
    print("TRANSACTION CATEGORIZATION PERFORMANCE REPORT")
    print("="*40)
    print(f"Total Transactions Processed: {stats['total']}")
    print(f"Successfully Parsed JSON:    {stats['parsed']} ({stats['parsed']/stats['total']:.1%})")
    print("-" * 40)
    
    evaluated = stats['parsed'] - stats['no_gt']
    if evaluated > 0:
        print(f"Exact Match Rate (L1-L4):   {stats['exact_match']/evaluated:.1%}")
        print(f"Partial Match Rate (L1-L2): {stats['partial_match']/evaluated:.1%}")
        print("-" * 40)
        print(f"L1 Accuracy (Block):        {stats['l1_match']/evaluated:.1%}")
        print(f"L2 Accuracy (Category):     {stats['l2_match']/evaluated:.1%}")
        print(f"L3 Accuracy (Sub-cat):      {stats['l3_match']/evaluated:.1%}")
        print(f"L4 Accuracy (Detail):       {stats['l4_match']/evaluated:.1%}")
    
    print("-" * 40)
    print(f"Codes without Ground Truth:  {stats['no_gt']}")
    print("="*40)

    if failures:
        print("\nTOP FAILURES (Sample):")
        for f in failures[:10]:
            print(f"Code {f['code']} | {f['desc']}")
            print(f"  ACTUAL:   {f['actual']}")
            print(f"  EXPECTED: {f['expected']}")
            print("-" * 20)

if __name__ == "__main__":
    analyze_results()
