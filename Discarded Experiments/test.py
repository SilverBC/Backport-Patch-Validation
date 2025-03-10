import os
from parser import parse_patch_file, read_file_content,split_patch_into_chunks, parse_patch_and_extract_functions, preprocess_patch, clean_extracted_code
from Judge import verify_patch, check_missing_elements, validate_omissions
from parser2 import compare_patches, format_differences
from unidiff import PatchSet


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


def process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, sample):
    """
    Process patches and verify them using the `verify_patch` function.
    Save results to a .txt file.
    """
    # Step 1: Extract file paths from the patches
    upstream_file_paths = parse_patch_file(upstream_patch_file)
    backported_file_paths = parse_patch_file(backported_patch_file)

    print_to_txt('parse_patch_file.txt', backported_patch_file, backported_file_paths)
    
    
    # Step 2: Process each file
    results = []
    is_valid = True
    for file_path, upstream_patch in upstream_file_paths.items():
        # chunked_upstream = split_patch_into_chunks(upstream_patch)
        # print_to_txt('parse_patch_file.txt', upstream_patch_file, upstream_file_paths)

        # print_to_txt("chunked.txt", file_path, chunked_upstream)
        
        # Step 3: Read the target code
        backported_patch, backported_path = get_value(backported_file_paths, file_path)
        
        
        full_path = os.path.join(base_directory, file_path)
        target_code = read_file_content(full_path)
                
        if target_code is None:
            print(f"Warning: Target code not found for file: {backported_path}")
            continue
        
        # finds which upstream changes are missing in backport
        result = compare_patches(upstream_patch, backported_patch)
        result2 = format_differences(result)
        
        print_to_txt('differences.txt', backported_path, result2)
        
        # # Function/method extractor based on full path and patch
        # parsed_functions = parse_patch_and_extract_functions(full_path, backported_patch)
        # parsed_functions = clean_extracted_code(parsed_functions)
        
        # print_to_txt('functions.txt', backported_path, parsed_functions)
        


        ### TODO IF preprocessing ever gets needed again
        # upstream_patch = preprocess_patch(upstream_patch)
        # backported_patch = preprocess_patch(backported_patch)
        # with open('preprocess.txt', 'a') as file:
            
        #     file.write(f"File:\n {backported_path}\n")
        #     file.write(f"Upstream:\n {upstream_patch}\n")
        #     file.write(f"Backported:\n {backported_patch}\n")
        #     file.write("-" * 80 + "\n")
        
        

    #     # Step 3a: Store the result
    #     results.append({
    #         "file_path": backported_path,
    #         "result": result
    #     })

                
    #     if result["completeness_verdict"] == "False" or result["completeness_verdict"] == "false":
    #         is_valid = False


    # # Step 4: Save results to a .txt file
    # if is_valid:
    #     verdict = "Correct"
    # else: 
    #     verdict = "Not Correct"

    # with open(output_file, 'a') as file:
    #     file.write(f"The Sample Folder Number: {sample} is {verdict} \n")
    #     for result in results:
    #         file.write(f"File: {result['file_path']}\n")
    #         file.write(f"Result: {result['result']}\n")
    #         file.write("-" * 80 + "\n")
    #     file.write("#" * 80 + "\n\n")

    # print(f"Results saved to {output_file}")

def main():
    # Paths to the upstream and backported patch files
    sample_folders = os.listdir('samples')

    # for sample in sample_folders:
    #     if sample.endswith(".csv"):
    #         continue

    #     upstream_patch_file = rf'samples\{sample}\upstream.patch'  # Replace with your upstream patch file path
    #     backported_patch_file = rf'samples\{sample}\backporter.patch'  # Replace with your backported patch file path

    #     base_directory = rf'samples\{sample}\target'  # Replace with the base directory of your target code

    #     output_file = "verification_results.txt"  # Replace with your desired output file path


    #     # Run the verification process
    #     process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, sample)
    
    upstream_patch_file = rf'samples\0005\upstream.patch'  # Replace with your upstream patch file path
    backported_patch_file = rf'samples\0005\backporter.patch'  # Replace with your backported patch file path

    base_directory = rf'samples\0005\target'  # Replace with the base directory of your target code

    output_file = "verification_results.txt"  # Replace with your desired output file path


        # Run the verification process
    process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, '0001')

if __name__ == "__main__":
    main()