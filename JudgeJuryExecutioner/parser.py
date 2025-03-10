import os
import re
import json
import csv
import json_repair

def repair_json(response):
    json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"
    matches = re.findall(json_pattern, response, re.DOTALL)

    if matches:
        json_str = matches[0]  # Take the first valid JSON block
    else:
        json_str = response  # Fallback to full response if no JSON is found


    try:
        return json_repair.loads(json_str)
    except json.JSONDecodeError:
        print("Invalid JSON response received!")
        return None


def get_file_from_path(files, path):
    """
    Helper function to find a file in a list of PatchedFile objects based on a path or substring match.
    """
    for file in files:
        if path in file.path:
            return file
    return None

##### CSV processing ####

def create_csv(csv_name, sample, verdict):
    file_exists = os.path.exists(csv_name)
    
    with open(csv_name, 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        if not file_exists:
            csv_writer.writerow(["sample_id", "review_verdict"])

        csv_writer.writerow([f"{sample.zfill(4)}", verdict])

def read_verdicts(file_path):
    """
    Read a CSV file and return a dictionary {sample_id: review_verdict}.
    """
    verdicts = {}
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            sample_id, verdict = row
            verdicts[sample_id] = verdict.lower()  # Normalize case
    return verdicts

def compare_verdicts(file1, file2):
    """
    Compare two CSV files containing {sample_id: review_verdict}.
    Print mismatches and overlap percentage.
    """
    verdicts1 = read_verdicts(file1)
    verdicts2 = read_verdicts(file2)

    total_samples = len(verdicts1)
    if total_samples == 0:
        print("No data to compare.")
        return

    # Find mismatches
    mismatches = {
        sample: (verdicts1[sample], verdicts2[sample])
        for sample in verdicts1 if sample in verdicts2 and verdicts1[sample] != verdicts2[sample]
    }

    # Calculate overlap percentage
    matching_count = total_samples - len(mismatches)
    overlap_percentage = (matching_count / total_samples) * 100

    print(f"Total Samples: {total_samples}")
    print(f"Mismatched Samples: {len(mismatches)}")
    print(f"Overlap Percentage: {overlap_percentage:.2f}%")

    if mismatches:
        print("\nDifferences:")
        for sample, (verdict1, verdict2) in mismatches.items():
            print(f"Sample {sample}: File1 = {verdict1}, File2 = {verdict2}")
            
            
#### temporary txt helper functions ###

def print_to_txt(txt_name, File_path, parsed_function):
        with open(txt_name, 'a', encoding="utf-8") as file:
            file.write(f"File:\n {File_path}\n")
            file.write(f"parsed functions:\n {parsed_function}\n")
            file.write("-" * 80 + "\n")
        
def write_verification_results_txt(output_file, sample, verdict, results):
    with open(output_file, 'a') as file:
        file.write(f"The Sample Folder Number: {sample} is {verdict} \n")
        for result in results:
            file.write(f"File: {result['file_path']}\n")
            file.write(f"Result: {result['result']}\n")
            file.write("-" * 80 + "\n")
        file.write("#" * 80 + "\n\n")
