import os
from parser import parse_patch_file, read_file_content
from Judge import verify_patch

def get_value(dictionary, path2):
    if path2 in dictionary:
        return dictionary[path2], path2
    
    # Try finding a key that contains path2 as a substring in case if direct lookup fails
    for key in dictionary:
        if path2 in key:
            return dictionary[key], key
    
    return None, None

def process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, sample):
    """
    Process patches and verify them using the `verify_patch` function.
    Save results to a .txt file.
    """
    # Step 1: Extract file paths from the patches
    upstream_file_paths = parse_patch_file(upstream_patch_file)
    backported_file_paths = parse_patch_file(backported_patch_file)

    # Step 2: Process each file
    results = []
    is_valid = True
    for file_path, upstream_patch in upstream_file_paths.items():
        # Step 3: Read the target code
        # backported_patch = backported_file_paths.get(file_path)
        backported_patch, backported_path = get_value(backported_file_paths, file_path)
        
        full_path = os.path.join(base_directory, file_path)
        target_code = read_file_content(full_path)

        if target_code is None:
            print(f"Warning: Target code not found for file: {backported_path}")
            continue

        result = verify_patch(upstream_patch, backported_patch, target_code)

        # Step 3a: Store the result
        results.append({
            "file_path": backported_path,
            "result": result
        })

                
        if result["is_correct"] == "No":
            is_valid = False


    # Step 4: Save results to a .txt file
    if is_valid:
        verdict = "Correct"
    else: 
        verdict = "Not Correct"

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

        upstream_patch_file = rf'samples\{sample}\upstream.patch'  # Replace with your upstream patch file path
        backported_patch_file = rf'samples\{sample}\backporter.patch'  # Replace with your backported patch file path

        base_directory = rf'samples\{sample}\target'  # Replace with the base directory of your target code

        output_file = "verification_results.txt"  # Replace with your desired output file path


        # Run the verification process
        process_patches(upstream_patch_file, backported_patch_file, base_directory, output_file, sample)

if __name__ == "__main__":
    main()