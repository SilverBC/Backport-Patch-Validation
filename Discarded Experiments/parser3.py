import os
import re
from tree_sitter import Language, Parser
from collections import defaultdict

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


def parse_patch_and_extract_functions(target_file_path, patch_set):
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

    # Iterate over files in the patch
    for patched_file in patch_set:
        # Iterate over hunks in the file
        for hunk in patched_file:
            # Extract the context line (after @@ ... @@)
            context_line = hunk.section_header.strip()

            # Match function/class names in the context line
            if target_file_path.endswith(".py"):
                class_match = re.match(r'^class\s+(\w+)', context_line)
                if class_match:
                    class_name = class_match.group(1)
                    class_code = extract_function_or_class_from_file(target_file_path, class_name, language)
                    if class_code:
                        extracted_definitions[class_name] = class_code
                else:
                    function_match = re.match(r'^def\s+(\w+)', context_line)
                    if function_match:
                        function_name = function_match.group(1)
                        function_code = extract_function_or_class_from_file(target_file_path, function_name, language)
                        if function_code:
                            extracted_definitions[function_name] = function_code

            elif target_file_path.endswith(".c"):
                if '(' in context_line:
                    before_paren = context_line.split('(')[0].strip()
                    parts = before_paren.split()
                    if parts:
                        function_name = parts[-1].split(')')[0]  
                        function_code = extract_function_or_class_from_file(target_file_path, function_name, language)
                        if function_code:
                            extracted_definitions[function_name] = function_code

    return {key: value.replace("\\n", "\n").replace("\\t", "\t") for key, value in extracted_definitions.items()}

def clean_extracted_code(code_str):
    """
    Clean up the extracted code string while preserving indentation.
    
    Parameters:
        code_str: A string or dictionary containing the extracted code (possibly cluttered).
    
    Returns:
        A dictionary with the structure:
        {file_name: {code_str_key_name: extracted_code}}
    """
    def clean_code_string(code_str):
        """
        Helper function to clean a single code string.
        """
        # Step 1: Normalize escaped newlines (if present)        code_str = code_str.replace("\\n", "\n")
        
        # Step 2: Split into lines and clean each line
        lines = code_str.split("\n")
        cleaned_lines = []
        for line in lines:
            # Remove trailing whitespace (preserve leading whitespace for indentation)
            cleaned_line = line.rstrip()
            if cleaned_line:  # Skip empty lines
                cleaned_lines.append(cleaned_line)
        
        # Step 3: Rejoin lines without altering leading whitespace
        return "\n".join(cleaned_lines)

    # Handle case where code_str is a string
    x = 0
    if isinstance(code_str, str):
        return {"default_file": {f"default_key_{x}": clean_code_string(code_str)}}

    # Handle case where code_str is a dictionary
    if isinstance(code_str, dict):
        cleaned_dict = {}
        for file_name, code_dict in code_str.items():
            if isinstance(code_dict, dict):
                cleaned_dict[file_name] = {}
                for code_key, code_value in code_dict.items():
                    # Clean each code value
                    cleaned_dict[file_name][code_key] = clean_code_string(code_value)
            else:
                # If code_dict is not a dictionary, treat it as a single code block
                cleaned_dict[file_name] = clean_code_string(code_dict)
                x = x+1
        return cleaned_dict

    # Handle unexpected input types
    raise ValueError(f"Unexpected input type: {type(code_str)}. Expected str or dict.")















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


def extract_function_from_hunk(hunk, file_path):
    """
    Extracts the enclosing function name from a hunk's context lines using Tree-sitter.
    """
    # Collect context lines (lines marked as context in the diff)
    context_lines = []
    for line in hunk:
        if line.is_context:
            # Use line.content to get the actual line content without diff markers
            context_lines.append(line.content.strip())
    
    code_block = '\n'.join(context_lines)
    
    # Determine language
    if file_path.endswith(".py"):
        language = PY_LANGUAGE
    elif file_path.endswith(".c"):
        language = C_LANGUAGE
    else:
        return None
    
    parser = Parser()
    parser.set_language(language)
    tree = parser.parse(bytes(code_block, "utf8"))
    root_node = tree.root_node
    
    # Define query to find function name
    if language == PY_LANGUAGE:
        query = PY_LANGUAGE.query("(function_definition name: (identifier) @name)")
    elif language == C_LANGUAGE:
        query = C_LANGUAGE.query("(function_definition declarator: (function_declarator declarator: (identifier) @name))")
    
    captures = query.captures(root_node)
    for node, tag in captures:
        if tag == "name":
            return node.text.decode("utf8").strip()
    return None




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