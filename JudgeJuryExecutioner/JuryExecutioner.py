import os
from unidiff import PatchSet
from Judge import Judge
from parser import create_csv, compare_verdicts, get_file_from_path , print_to_txt, write_verification_results_txt


VERDICTS_CSV_FILE = r"samples/verdicts.csv"  
OUTPUT_CSV_FILE = r"samples/verdicts_JudgeJuryExecutioner.csv"
OUTPUT_FILE = "verification_results.txt"
SAMPLES_DIR = "samples"

def get_verdict(result):
    """Determines the verdict based on the 'is_correct' field in result for both dict and str result"""

    if isinstance(result, dict):
        if result.get("is_correct") == "No":
            return "incorrect"

    if isinstance(result, str):
        if "'is_correct': 'No'" in result:
            return "incorrect"

    return "unknown" 

def process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, sample):
    """
    Process patches and verify them.
    Save results to a .txt file.
    """
    # Step 1: Parse patch files using unidiff
    with open(upstream_patch_file, 'r') as f:
        upstream_patch = PatchSet(f)
    with open(backported_patch_file, 'r') as f:
        backported_patch = PatchSet(f)

    # Step 2: Process each file in the upstream patch
    results = []
    verdict = "correct"
    for upstream_file in upstream_patch:
        if upstream_file.path.endswith(".rst"):
            continue
        
        # Step 3: Find the corresponding file in the backported patch
        backported_file = get_file_from_path(backported_patch, upstream_file.path)
        if not backported_file:
            print(f"Warning: File {upstream_file.path} not found in backported patch.")
            continue

        # Step 4: Read the target code
        full_path = os.path.join(base_directory, backported_file.path)
        if not os.path.exists(full_path):
            print(f"Warning: File {full_path} does not exist in the base directory.")
            continue
        target_code = open(full_path, 'r').read()
        
        # step 5: judge and write down the results 
        judge = Judge()
        
        result = judge.process_backport(upstream_file, backported_file, target_code)
        print_to_txt("functions.txt", backported_file.path, result)
        
        
        results.append({
            "file_path": backported_file.path,
            "result": result
        })

        if get_verdict(result) == "incorrect":
            verdict = "incorrect"


    # Step 5: Append result to CSV file and txt file    
    create_csv(OUTPUT_CSV_FILE, sample, verdict)
    write_verification_results_txt(output_file, sample, verdict, results)
    print(f"Results saved to {output_file}")

def main():
    
    sample_folders = [f for f in os.listdir(SAMPLES_DIR) if os.path.isdir(os.path.join(SAMPLES_DIR, f)) and not f.endswith(".csv")]

    # process each sample file sequentially
    for sample in sample_folders:
        if int(sample.lstrip("0")) < 20:        # for testing purposes
            continue

        upstream_patch_file = os.path.join(SAMPLES_DIR, sample, "upstream.patch")
        backported_patch_file = os.path.join(SAMPLES_DIR, sample, "backporter.patch")
        base_directory = os.path.join(SAMPLES_DIR, sample, "target")

        process_patches(upstream_patch_file, backported_patch_file, base_directory, OUTPUT_FILE, sample) 

    compare_verdicts(VERDICTS_CSV_FILE, OUTPUT_CSV_FILE)

if __name__ == "__main__":
    main()