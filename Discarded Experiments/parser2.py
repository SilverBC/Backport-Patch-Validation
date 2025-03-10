import re
from difflib import unified_diff

def parse_patch(patch_content):
    """
    Parse a patch file and extract changes (added/removed/modified lines).

    Parameters:
        patch_content: String containing the contents of the patch file.

    Returns:
        Dictionary { file_path: { line_number: (old_line, new_line) } }
    """
    changes = {}
    current_file = None
    current_chunk = None

    for line in patch_content.splitlines():
        # Match file paths in the patch header
        file_match = re.match(r"diff --git a/(.*) b/(.*)", line)
        if file_match:
            current_file = file_match.group(1)
            changes[current_file] = {}
            continue

        # Match chunk headers (e.g., @@ -14,12 +14,14 @@)
        chunk_match = re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", line)
        if chunk_match:
            start_line = int(chunk_match.group(3))  # New file line number
            current_chunk = start_line
            continue

        # Match added/removed lines while preserving the exact code
        if current_file and current_chunk is not None:
            # Avoid matching the file header lines that start with "+++"
            if line.startswith("+") and not line.startswith("+++"):
                changes[current_file][current_chunk] = (None, line[1:])
                current_chunk += 1
            elif line.startswith("-") and not line.startswith("---"):
                changes[current_file][current_chunk] = (line[1:], None)
            elif line.startswith(" "):
                current_chunk += 1

    return changes

def compare_patches(upstream_patch, backporter_patch):
    """
    Compare two patch files and return changes in upstream_patch that are not in backporter_patch.

    Parameters:
        upstream_patch: String containing the contents of upstream.patch.
        backporter_patch: String containing the contents of backporter.patch.

    Returns:
        Dictionary { file_path: { "additions": [...], "deletions": [...] } }
    """
    upstream_changes = parse_patch(upstream_patch)
    backporter_changes = parse_patch(backporter_patch)

    differences = {}
    unedited_differences = {}

    for file_path, upstream_file_changes in upstream_changes.items():
        additions = []
        deletions = []
        backporter_file_changes = backporter_changes.get(file_path, {})

        for line_number, (old_line, new_line) in upstream_file_changes.items():
            bp_old, bp_new = backporter_file_changes.get(line_number, (None, None))
            # If the new line differs, record it as an addition
            if new_line != bp_new:
                if new_line is not None:
                    additions.append(new_line)
            # If the old line differs, record it as a deletion
            if old_line != bp_old:
                if old_line is not None:
                    deletions.append(old_line)

        if additions or deletions:
            differences[file_path] = {"additions": additions, "deletions": deletions}

    return differences

# Optional: Format the differences into a human-readable string while preserving the exact code.
def format_differences(differences):
    """
    Format the differences into a cleaner, more readable string while preserving the original code.
    
    Parameters:
        differences: Dictionary { file_path: { "additions": [...], "deletions": [...] } }
    
    Returns:
        Formatted string.
    """
    output = []
    for file_path, file_differences in differences.items():
        output.append(f"File: {file_path}")
        if file_differences.get("additions"):
            output.append("  + Additions:")
            for addition in file_differences["additions"]:
                output.append(f"    {addition}")
        if file_differences.get("deletions"):
            output.append("  - Deletions:")
            for deletion in file_differences["deletions"]:
                output.append(f"    {deletion}")
        output.append("")  # Blank line between files for readability
    return "\n".join(output)

# Example usage:
# differences = compare_patches(upstream_patch_content, backporter_patch_content)
# print(differences)  # To get the dictionary output directly
# Or, if you need a string:
# print(format_differences(differences))