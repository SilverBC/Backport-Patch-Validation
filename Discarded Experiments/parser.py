import os
import re
from tree_sitter import Language, Parser

# Load both Python and C grammars
PY_LANGUAGE = Language('build/tree_sitter_python.dll', 'python')
C_LANGUAGE = Language('build/tree_sitter_c.dll', 'c')

def extract_function_or_class_from_file(target_file_path, name, language):
    """
    Extracts a function or class definition from the target file using Tree-sitter.
    
    Parameters:
        - target_file_path: Path to the .py or .c file
        - name: Name of the function or class to extract
        - language: Tree-sitter language object (PY_LANGUAGE or C_LANGUAGE)
    
    Returns:
        - Extracted code as a clean string, or None if not found.
    """
    if not os.path.exists(target_file_path):
        return None
    
    with open(target_file_path, "r", encoding="utf-8") as f:
        code = f.read()

    parser = Parser()
    parser.set_language(language)
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node

    extracted_code = None

    if language == PY_LANGUAGE:
        query = PY_LANGUAGE.query("""
            (function_definition name: (identifier) @name)
            (class_definition name: (identifier) @name)
        """)
    elif language == C_LANGUAGE:
        query = C_LANGUAGE.query("""
            (function_definition
                declarator: (function_declarator
                    declarator: (identifier) @name))
        """)
    else:
        return None

    captures = query.captures(root_node)

    for node, tag in captures:
        if tag == "name" and node.text.decode("utf8") == name:
            current_node = node
            while current_node and (current_node.type not in ["function_definition", "class_definition"]):
                current_node = current_node.parent
            if current_node:
                start_byte = current_node.start_byte
                end_byte = current_node.end_byte
                extracted_code = code[start_byte:end_byte]
                break

    return extracted_code.strip("\n ") if extracted_code else None

def extract_code_by_lines(target_file_path, start_line, end_line, context_lines=60):
    """
    Extracts code from the target file based on the specified line numbers, including additional context lines.
    
    Parameters:
        - target_file_path: Path to the .py or .c file
        - start_line: Starting line number (1-based index)
        - end_line: Ending line number (1-based index)
        - context_lines: Number of additional lines to include before and after the specified range
    
    Returns:
        - Extracted code as a string, or None if the file or lines are invalid.
    """
    print(f"MAMBA: {start_line} and {end_line}. file_path: {target_file_path}")
    if not os.path.exists(target_file_path):
        return None
    
    with open(target_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Adjust start and end lines to include context
    start_line_with_context = max(1, start_line - context_lines)
    end_line_with_context = min(len(lines), end_line + context_lines)

    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return None
    
    # Extract the lines with context
    extracted_lines = lines[start_line_with_context-1:end_line_with_context]
    extracted_code = ''.join(extracted_lines).strip("\n ")

    print(f"MAMBA: {start_line_with_context} and {end_line_with_context}. file_path: {target_file_path}")
    print(extracted_code)

    return extracted_code

def parse_patch_and_extract_functions(target_file_path, patched_hunk):
    """
    Parses a patch file, extracts function, method, or class names from @@ ... @@ headers, 
    and retrieves the full function/class definitions from the target source file.

    Parameters:
        - target_file_path: Path to the original source file
        - patch_set: PatchSet object containing the parsed patch file

    Returns:
        - Dictionary { function_name_or_class: extracted_code } with clean formatting.
    """
    extracted_definitions = {}

    if target_file_path.endswith(".py"):
        language = PY_LANGUAGE
    elif target_file_path.endswith(".c"):
        language = C_LANGUAGE
    else:
        return extracted_definitions

    # Extract line numbers directly from the hunk
    start_line = patched_hunk.target_start  # Starting line in the target file
    end_line = start_line + patched_hunk.target_length - 1  # Ending line in the target file

    # Extract the context line (after @@ ... @@)
    context_line = patched_hunk.section_header.strip()

    # Debug print
    print(f"Processing hunk: start_line={start_line}, end_line={end_line}, context_line='{context_line}'")

    # Match function/class names in the context line
    if target_file_path.endswith(".py"):
        class_match = re.match(r'^class\s+(\w+)', context_line)
        if class_match:
            class_name = class_match.group(1)
            print(f"Found class: {class_name}")
            class_code = extract_function_or_class_from_file(target_file_path, class_name, language)
            if class_code:
                extracted_definitions[class_name] = class_code
            else:
                # Fallback to line-based extraction if function/class extraction fails
                print(f"Class extraction failed, falling back to line-based extraction")
                code_by_lines = extract_code_by_lines(target_file_path, start_line, end_line)
                if code_by_lines:
                    extracted_definitions[f"lines_{start_line}_{end_line}"] = code_by_lines
        else:
            function_match = re.match(r'^def\s+(\w+)', context_line)
            if function_match:
                function_name = function_match.group(1)
                print(f"Found function: {function_name}")
                function_code = extract_function_or_class_from_file(target_file_path, function_name, language)
                if function_code:
                    extracted_definitions[function_name] = function_code
                else:
                    # Fallback to line-based extraction if function/class extraction fails
                    print(f"Function extraction failed, falling back to line-based extraction")
                    code_by_lines = extract_code_by_lines(target_file_path, start_line, end_line)
                    if code_by_lines:
                        extracted_definitions[f"lines_{start_line}_{end_line}"] = code_by_lines
            else:
                # No function/class match, fallback to line-based extraction
                print(f"No function/class match, falling back to line-based extraction")
                code_by_lines = extract_code_by_lines(target_file_path, start_line, end_line)
                if code_by_lines:
                    extracted_definitions[f"lines_{start_line}_{end_line}"] = code_by_lines

    elif target_file_path.endswith(".c"):
        if '(' in context_line:
            before_paren = context_line.split('(')[0].strip()
            parts = before_paren.split()
            if parts:
                function_name = parts[-1].split(')')[0]  
                print(f"Found function: {function_name}")
                function_code = extract_function_or_class_from_file(target_file_path, function_name, language)
                if function_code:
                    extracted_definitions[function_name] = function_code
                else:
                    # Fallback to line-based extraction if function/class extraction fails
                    print(f"Function extraction failed, falling back to line-based extraction")
                    code_by_lines = extract_code_by_lines(target_file_path, start_line, end_line)
                    if code_by_lines:
                        extracted_definitions[f"lines_{start_line}_{end_line}"] = code_by_lines
        else:
            # No function match, fallback to line-based extraction
            print(f"No function match, falling back to line-based extraction")
            code_by_lines = extract_code_by_lines(target_file_path, start_line, end_line)
            if code_by_lines:
                extracted_definitions[f"lines_{start_line}_{end_line}"] = code_by_lines

    return {key: value.replace("\\n", "\n").replace("\\t", "\t") for key, value in extracted_definitions.items()}

def clean_extracted_code(code_str):
    """
    Clean up the extracted code string while preserving indentation.
    
    Parameters:
        code_str: A string containing the extracted code (possibly cluttered).
    
    Returns:
        A cleaned string with proper indentation.
    """
    
    print(type(code_str))
    if isinstance(code_str, dict):
        # Extract code string from dictionary if needed
        keys = list(code_str.keys())
        print("RAAAAAAAAAH")
        print(keys)
        print()
        if keys:
            code_str = code_str.get(keys[0], "")
        else:
            print("clean_extracted_code unable to clean that which does not exist")
            return ""

    # Step 1: Normalize escaped newlines (if present)
    code_str = code_str.replace("\\n", "\n")
    
    # Step 2: Split into lines and clean each line
    lines = code_str.split("\n")
    cleaned_lines = []
    for line in lines:
        # Remove trailing whitespace (preserve leading whitespace for indentation)
        cleaned_line = line.rstrip()
        if cleaned_line:  # Skip empty lines
            cleaned_lines.append(cleaned_line)
    
    # Step 3: Rejoin lines without altering leading whitespace
    code_str = "\n".join(cleaned_lines)
    
    return code_str
















def split_patch_into_chunks(patches):
    """
    Splits the patch content into individual chunks based on chunk headers.

    Parameters:
        patches: Either a single patch string or a dictionary {file_name: patch_content}.

    Returns:
        If input is a dictionary: {file_name: {file_name_change_x: patch_chunk}}.
        If input is a string: {"patch_change_x": patch_chunk}.
    """
    chunk_header_regex = re.compile(r"^@@ -\d+,\d+ \+\d+,\d+ @@.*$", re.MULTILINE)
    
    if isinstance(patches, dict):
        # Input is a dictionary of patches (e.g., {file_name: patch_content})
        chunked_patches = {}
        for file_name, patch_content in patches.items():
            # Find all chunk headers in the patch content
            chunk_headers = [(m.start(), m.end()) for m in chunk_header_regex.finditer(patch_content)]
            
            # Split the patch content into chunks based on headers
            file_chunks = {}
            for i, (start_pos, end_pos) in enumerate(chunk_headers):
                # Determine the end of the current chunk
                next_start_pos = chunk_headers[i + 1][0] if i + 1 < len(chunk_headers) else len(patch_content)
                
                # Extract the chunk content
                chunk_content = patch_content[start_pos:next_start_pos].strip()
                
                # Store the chunk with a unique key (e.g., file_name_change_1, file_name_change_2, etc.)
                chunk_key = f"{file_name}_change_{i + 1}"
                file_chunks[chunk_key] = chunk_content
            
            # Add the file's chunks to the final dictionary
            chunked_patches[file_name] = file_chunks
        
        return chunked_patches
    
    elif isinstance(patches, str):
        # Input is a single patch string
        chunk_headers = [(m.start(), m.end()) for m in chunk_header_regex.finditer(patches)]
        
        # Split the patch content into chunks based on headers
        patch_chunks = {}
        for i, (start_pos, end_pos) in enumerate(chunk_headers):
            # Determine the end of the current chunk
            next_start_pos = chunk_headers[i + 1][0] if i + 1 < len(chunk_headers) else len(patches)
            
            # Extract the chunk content
            chunk_content = patches[start_pos:next_start_pos].strip()
            
            # Store the chunk with a unique key (e.g., patch_change_1, patch_change_2, etc.)
            chunk_key = f"patch_change_{i + 1}"
            patch_chunks[chunk_key] = chunk_content
        
        return patch_chunks
    
    else:
        raise ValueError("Input must be either a dictionary or a string.")


def parse_patch_file(patch_file_path):
    with open(patch_file_path, 'r') as file:
        patch_content = file.read()

    # Regular expression to match the start of a file patch
    file_patch_start_regex = re.compile(r'^diff --git a/(.*) b/(.*)$', re.MULTILINE)

    # Find all the starting positions of file patches
    file_patch_starts = [(m.start(), m.group(1)) for m in file_patch_start_regex.finditer(patch_content)]

    # Extract patches for each file
    patches_per_file = {}
    for i, (start_pos, file_path) in enumerate(file_patch_starts):
        # Determine the end position of the current file patch
        if (file_path.endswith('.rst')):
            continue
        
        end_pos = file_patch_starts[i + 1][0] if i + 1 < len(file_patch_starts) else len(patch_content)

        # Extract the patch content for the current file
        patch_content_for_file = patch_content[start_pos:end_pos].strip()

        # Store the patch content in the dictionary
        patches_per_file[file_path] = patch_content_for_file

    return patches_per_file

def read_file_content(file_path):
    """Read the entire content of a file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read()
    else:
        return None
    
def preprocess_patch(patch_content):
    """
    Preprocess the patch to remove metadata and focus on code changes.
    """
    lines = patch_content.splitlines()
    code_changes = []
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            code_changes.append(line[1:])  # Remove the '+' prefix
    return "\n".join(code_changes)


# def clean_extracted_code(extracted_data):
#     """
#     Cleans up extracted code by removing unnecessary escape sequences, 
#     fixing unintended line breaks, and ensuring proper indentation.

#     Parameters:
#         extracted_data (str | dict): Either a raw extracted function string or 
#                                      a dictionary { function_name: function_code }.

#     Returns:
#         str | dict: Cleaned function string if input was a string, or 
#                     cleaned dictionary if input was a dictionary.
#     """
#     if isinstance(extracted_data, dict):
#         # If it's a dictionary, clean each function's code separately
#         return {key: clean_extracted_code(value) for key, value in extracted_data.items()}

#     if not isinstance(extracted_data, str):
#         raise TypeError(f"Expected str or dict, but got {type(extracted_data).__name__}")

#     # Step 1: Decode escape sequences properly
#     cleaned_code = extracted_data.encode().decode('unicode_escape')

#     # Step 2: Remove misplaced newlines inside dictionaries and function calls
#     cleaned_code = re.sub(r"(\n\s*){2,}", "\n\n", cleaned_code)  # Reduce excessive blank lines
#     cleaned_code = re.sub(r"(\n\s*)'([^']+)':\s*'\n\s*", r"'\2': '", cleaned_code)  # Fix split dictionary values
#     cleaned_code = re.sub(r"(\n\s*)\"([^\"]+)\":\s*\"\n\s*", r'"\2": "', cleaned_code)  # Fix split dictionary values

#     # Step 3: Ensure function/class structure remains intact
#     cleaned_code = re.sub(r"(\n\s*)def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)\s*:\s*\n", r"\n\ndef \2():\n", cleaned_code)
#     cleaned_code = re.sub(r"(\n\s*)class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\):\s*\n", r"\n\nclass \2:\n", cleaned_code)

#     # Step 4: Normalize indentation
#     lines = cleaned_code.split("\n")
#     formatted_lines = []
#     indent_level = 0
#     indent_size = 4  # Python standard indentation

#     for line in lines:
#         stripped = line.lstrip()

#         if stripped:
#             if stripped.startswith("def ") or stripped.startswith("class "):
#                 indent_level = 0  # Reset indentation for function/class definitions
#             elif stripped.startswith(("return", "raise", "pass", "break", "continue")):
#                 indent_level = max(indent_level - indent_size, 0)

#             formatted_lines.append(" " * indent_level + stripped)

#             if stripped.endswith(":"):
#                 indent_level += indent_size
#         else:
#             formatted_lines.append("")  # Preserve empty lines

#     cleaned_code = "\n".join(formatted_lines)
#     return cleaned_code




def main():
    patch_file_path = r'samples\0001\upstream.patch'  # Replace with your .patch file path
    patches_per_file = parse_patch_file(patch_file_path)

    # Print the extracted patches per file
    for file_path, patch_content in patches_per_file.items():
        print(f"File: {file_path}")
        print(patch_content)
        print("-" * 80)

if __name__ == "__main__":
    main()