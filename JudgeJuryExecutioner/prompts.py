# Compare Intent Prompt
COMPARE_INTENT_PROMPT = """Analyze the following upstream patch and backported patch. 
Identify any discrepancies in intent, key logic changes, or security/functionality goals.
Consider the upstream patch as holy, without faults and judge the backported patch.
Focus on changes made by the upstream and backported patches. Some cases to consider:
1) The changes in one may not be available in another because identical code already exists.
2) Differences in functions may be due to implementation differences between versions. Check if the same intent is achieved despite differences.

Consider these critical:
- Version identifiers (RCSID/CVS tags)
- API/ABI version markers
- Backward compatibility breaks

Upstream Patch:
{upstream_patch}

Backported Patch:
{backported_patch}

Output strictly as JSON, without any extra summaries or artifacts:
{{
    "discrepancies": ["List of intent/logic differences"],
    "security_risk": "Yes/No",
    "functionality_risk": "Yes/No"
}}

IMPORTANT: Respond only with valid JSON. Do not write a preamble or summary.
"""

# Abstract Code Context Prompt
ABSTRACT_CODE_PROMPT = """You are an expert at patch backporting. Process this code and patch to create focused context:
1. Keep all class/function/variable names.
2. Keep full implementation for functions modified in the patch or those DIRECTLY relevant to understanding the changes.
3. Abstract other functions to signatures with '# ...'.
4. Preserve control structures (if/for/try).
5. Keep comments about intent/edge cases.
6. Preserve any functions/variables directly called or modified by the backport patch.
7. Include data structures passed between preserved functions.

Backport Patch:
{backport_patch}

Target Code:
{target_code}

Output ONLY the abstracted code.
"""

# Validate with Context Prompt
VALIDATE_WITH_CONTEXT_PROMPT = """You are an expert in verifying backported patches who is tasked with judging discrepancies between an upstream patch and a backported patch.
The target code has been abstracted to preserve only the most relevant context, such as class names, variables defined outside functions, and critical functions.
Non-critical functions have been abstracted to only their names, while critical functions (those essential for understanding the logic) have been preserved in full.

**Abstraction Process**:
1. Class names and variables defined outside functions are preserved.
2. Function names are preserved, but their implementations are abstracted unless they are critical for context.
3. Critical functions (e.g., those containing key logic or security-related code) are kept in full.

**Task**:
Review the discrepancies between the upstream and backported patches. Use the abstracted target code to determine if these discrepancies are justified or problematic.

**Input**:
Discrepancies include judgment from a previous expert comparing the backported and upstream patches.
- Discrepancies: {discrepancies}
- Backported Patch: {backported_patch}
- Abstracted Target Code: {target_code}

**Instructions**:
1. Differences in function names or implementations are not necessarily errors if they achieve the same intent and are part of the target codebase's design.
2. For each discrepancy, explain if it's justified by the target code (e.g., renamed functions, version-specific syntax, or other contextual reasons).
3. Flag any unresolved discrepancies that could impact security or functionality.
4. Provide suggested fixes for any problematic discrepancies.

**Output Format**:
You MUST follow this example format.
Output strictly as JSON, without any extra summaries or artifacts:
{{
    "is_correct": "No",
    "difference_type": "Major",
    "explanation": "The missing RCSID change could potentially cause maintenance issues.",
    "suggested_fixes": "Change the RCSID to match the upstream patch."
}}

Respond only with valid JSON. Do not write a preamble or summary.
"""
