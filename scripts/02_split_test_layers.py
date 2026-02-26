import pandas as pd
import os

# Paths relative to project root
GT_PATH = "taxonomy/data/ground_truth_normalized.csv"
CATALOG_PATH = "taxonomy/data/transaction_code_catalog.csv"
OUTPUT_DIR = "taxonomy/data/"

def main():
    if not os.path.exists(GT_PATH) or not os.path.exists(CATALOG_PATH):
        print("Error: Ground truth or catalog file missing. Run extraction first.")
        return

    print("Loading datasets...")
    # Read everything as string to avoid type issues
    df_gt = pd.read_csv(GT_PATH, dtype=str).fillna('')
    df_catalog = pd.read_csv(CATALOG_PATH, dtype=str).fillna('')

    # 1. Identify Layer 3 (Unknown) 
    # These are rows in ground truth where L1 is empty
    l3_codes = df_gt[df_gt['L1'] == '']['TRANCD'].unique()
    df_l3 = df_catalog[df_catalog['TRANCD'].isin(l3_codes)].copy()
    print(f"Layer 3 (Unknown): {len(df_l3)} codes found (L1 is empty in GT).")
    print(f"Layer 3 codes: {list(l3_codes)}")

    # 2. Identify Layer 2 (Ambiguous)
    # These are codes that have MORE THAN ONE entry in the ground truth
    code_counts = df_gt[df_gt['L1'] != '']['TRANCD'].value_counts()
    ambiguous_codes = code_counts[code_counts > 1].index.tolist()
    
    df_l2 = df_catalog[df_catalog['TRANCD'].isin(ambiguous_codes)].copy()
    print(f"Layer 2 (Ambiguous): {len(df_l2)} codes identified (multiple mappings in GT).")
    print(f"Layer 2 codes: {ambiguous_codes}")

    # 3. Identify Layer 1 (Obvious)
    # These are codes that have EXACTLY ONE mapping in GT and L1 is not empty
    obvious_codes = code_counts[code_counts == 1].index.tolist()
    df_l1 = df_catalog[df_catalog['TRANCD'].isin(obvious_codes)].copy()
    print(f"Layer 1 (Obvious): {len(df_l1)} codes identified (single mapping in GT).")

    # 4. Save test sets
    df_l1.to_csv(os.path.join(OUTPUT_DIR, "layer_1_test_set.csv"), index=False)
    df_l2.to_csv(os.path.join(OUTPUT_DIR, "layer_2_test_set.csv"), index=False)
    df_l3.to_csv(os.path.join(OUTPUT_DIR, "layer_3_test_set.csv"), index=False)
    
    print("\nTest sets saved successfully to taxonomy/data/")

if __name__ == "__main__":
    main()
