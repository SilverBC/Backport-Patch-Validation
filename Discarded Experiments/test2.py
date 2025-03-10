import os
from parser import parse_patch_file, read_file_content,split_patch_into_chunks, preprocess_patch, clean_extracted_code # ,parse_patch_and_extract_relevant_chunks
from Judge2 import extract_relevant_code, verify_patch, check_missing_elements, validate_omissions, verify_patch_2a, verify_patch_2b
from parser2 import compare_patches, format_differences
from unidiff import PatchSet
from parser import parse_patch_and_extract_functions
from Judge2 import validate_with_context, compare_intent, abstract_code_context
import csv
import time


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

###########

def get_value(dictionary, path2):
    if path2 in dictionary:
        return dictionary[path2], path2
    
    # Try finding a key that contains path2 as a substring in case if direct lookup fails
    for key in dictionary:
        if path2 in key:
            return dictionary[key], key
    
    return None, None

def print_to_txt(txt_name, File_path, parsed_function):
        with open(txt_name, 'a', encoding="utf-8") as file:
            file.write(f"File:\n {File_path}\n")
            file.write(f"parsed functions:\n {parsed_function}\n")
            file.write("-" * 80 + "\n")


def get_value(files, path2):
    """
    Helper function to find a file in a list of PatchedFile objects based on a path or substring match.
    """
    for file in files:
        if path2 in file.path:
            return file
    return None

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
        backported_file = get_value(backported_patch, upstream_file.path)
        if not backported_file:
            print(f"Warning: File {upstream_file.path} not found in backported patch.")
            continue

        # Step 4: Read the target code
        full_path = os.path.join(base_directory, backported_file.path)
        if not os.path.exists(full_path):
            print(f"Warning: File {full_path} does not exist in the base directory.")
            continue
        # # finds which upstream changes are missing in backport
        # result = compare_patches(upstream_file, backported_patch)
        # result2 = format_differences(result)
        # print_to_txt('differences.txt', backported_path, result2)
        
        
        # Function/method extractor based on full path and patch
        
        ## ZAZA
        target_code = open(full_path, 'r').read()
        flag = False
        file_functions = ""
        # for backported_hunk in backported_file:
        #     flag = False
        #     parsed_functions = parse_patch_and_extract_functions(full_path, backported_hunk)
        #     keys = parsed_functions.keys()
        #     print(f"KEYS: {keys}")
        #     for key in keys:
        #         if "lines_" in key:
        #             flag = True
            
        #     parsed_functions = clean_extracted_code(parsed_functions)
            
        #     # print_to_txt('functions2.txt', backported_file.path, parsed_functions)
        #     # print(parsed_functions)
            
        #     # Needed if function/class was not detected
        #     if flag: 
        #         parsed_functions = extract_relevant_code(backported_hunk, parsed_functions)
                
        #     file_functions += "".join(parsed_functions) + "\n"
        # print_to_txt('functions3.txt', backported_file.path, file_functions)
        
        discreptrancies = compare_intent(upstream_file, backported_file)
        time.sleep(5)
        print_to_txt("functions4.txt", backported_file.path,  discreptrancies)
        abstract_code = abstract_code_context(target_code, backported_file)
        time.sleep(5)
        print_to_txt("functions5.txt", backported_file.path,  abstract_code)
        result = validate_with_context(discreptrancies, backported_file.path, target_code)
        time.sleep(5)
        print_to_txt("functions6.txt", backported_file.path,  result)
        #1018
        
    #     file_contexts = []

    #     # Iterate over the keys in parsed_functions
    #     for key in parsed_functions.keys():
    #         # Print to the text file
    #         # print_to_txt('functions.txt', backported_file.path, parsed_functions[key])
            
    #         # Append the parsed function to the list
    #         file_contexts.append(parsed_functions[key])

    #     # Join all file contexts with newlines
    #     file_context = "\n".join(file_contexts)
        
        # result = verify_patch_2a(upstream_file, backported_file, file_context)
        # if result["is_correct"] == "Yes":
        #     result = verify_patch_2b(upstream_file, backported_file, file_context, result)
        

        # Step 3a: Store the result
        results.append({
            "file_path": backported_file.path,
            "result": result
        })


        if result["is_correct"] == "No":
            verdict = "incorrect"

        # if type(result) == dict and result["is_correct"] == "No":
        #     is_valid = False
        # elif """"is_correct": "no""" in result:
        #     is_valid = False

    # # # Step 4: Save results to a .txt file
    # if is_valid:
    #     verdict = "Correct"
    # else: 
    #     verdict = "Not Correct"

    # # Step 4: Determine verdict
    # review_verdict = "correct" if is_valid else "incorrect"

    # Step 5: Append result to CSV file
    file_exists = os.path.exists(output_file)

    with open("verdicts2.csv", 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)

        # Write header only if file is newly created
        if not file_exists:
            csv_writer.writerow(["sample_id", "review_verdict"])

        # Append the result
        csv_writer.writerow([f"{sample.zfill(4)}", verdict])


    with open(output_file, 'a') as file:
        file.write(f"The Sample Folder Number: {sample} is {verdict} \n")
        for result in results:
            file.write(f"File: {result['file_path']}\n")
            file.write(f"Result: {result['result']}\n")
            file.write("-" * 80 + "\n")
        file.write("#" * 80 + "\n\n")

    print(f"Results saved to {output_file}")

def main():
    # Paths to the upstream and backported patch files
    sample_folders = os.listdir('samples')
    

    for sample in sample_folders:
        if sample.endswith(".csv"):
            continue
        
        if int(sample.lstrip("0")) <= 3:
            continue
        
        upstream_patch_file = rf'samples\{sample}\upstream.patch'  # Replace with your upstream patch file path
        backported_patch_file = rf'samples\{sample}\backporter.patch'  # Replace with your backported patch file path

        base_directory = rf'samples\{sample}\target'  # Replace with the base directory of your target code

        output_file = "verification_results.txt"  # Replace with your desired output file path


        # Run the verification process
        process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, sample)
    
    
    # upstream_patch_file = rf'samples\0006\upstream.patch'  # Replace with your upstream patch file path
    # backported_patch_file = rf'samples\0006\backporter.patch'  # Replace with your backported patch file path

    # base_directory = rf'samples\0006\target'  # Replace with the base directory of your target code

    # output_file = "verification_results3.txt"  # Replace with your desired output file path


    # # Run the verification process
    # process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, '0001')

    file1 = r"samples\verdicts.csv"  
    file2 = r"verdicts2.csv"  

    compare_verdicts(file1, file2)

if __name__ == "__main__":
    main()