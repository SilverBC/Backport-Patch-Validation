import re
import json
from openai import OpenAI
import json_repair
import time


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="INSERT API KEY",
    )



def query_model(prompt):
    completion = client.chat.completions.create(
        model="deepseek/deepseek-r1:free",
        # model="deepseek/deepseek-chat:free",
        seed=2025,
        messages=[{"role": "user", "content": prompt}]
    )
    
    if not completion:
        raise ValueError("API response is None. Check API call.")
    
    if not completion.choices or not completion.choices[0].message.content:
        raise ValueError(f"Unexpected API response: {completion}")
    
    return parse_response(completion.choices[0].message.content)

def parse_response(response):
    json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"  # Matches nested JSON structures
    matches = re.findall(json_pattern, response, re.DOTALL)

    if matches:
        json_str = matches[0]
    else:
        json_str = response 
    
    parsed_response = json_repair.loads(json_str)
    return parsed_response

def check_missing_elements(upstream, backported):
    prompt = f"""ROLE: You are a backporting specialist analyzing whether the backported patch includes all essential elements from the upstream patch. 
    
    [Upstream Changes]
    {upstream}

    [Backported Changes]
    {backported}

    common missing elements missing from the upstream patch to backported version:
    1. Function/method calls
    2. Conditional logic branches
    3. Error handling blocks or security measures
    4. Variable initializations and imports 
    5. API/Interface changes
    additionally, there may be other changes missing. 

    YOU MUST under all circumstances, Provide your verdict strictly as a JSON object with the following keys and nothing extra:
    {{
        "missing_elements": "missing_change_1", "missing_change_2", 
        "acceptable_omissions": "irrelevant_missing_change",
        "completeness_verdict": bool
    }}"""
    return query_model(prompt)

def validate_omissions(missing_elements, target_code):
    prompt = f"""ROLE: You are a backporting specialist analyzing whether the missing changes in the backported patch are safe to exclude. 

    GOAL: Analyze the missing elements and judge if the backported patch can still be considered a valid backport of the upstream patch:
    
    
    
    Consider these factors:
    1. Does the target code already have equivalent functionality? (equivalent in deep sense)
    2. Are there code specific differences justifying omission? 
    
    CONTEXT:
    [MISSING ELEMENTS]
    {missing_elements}
    
    [RELEVANT TARGET CODE]
    {target_code}               ##TODO IMPLEMENT CHROMADB Search you wrote down on your paper. Diamonds are made under pressure, fate finds a way.               
    
    
    YOU MUST under all circumstances, Provide your verdict strictly as a JSON object with the following keys and nothing extra:
    {{
        "justified_omissions": list[str],
        "unjustified_omissions": list[str],
        "omission_verdict": bool
    }}"""
    return query_model(prompt)

def check_location(upstream, backported, target):
    prompt = f"""Analyze patch placement accuracy:
    
    [Upstream Context]
    {upstream}

    [Backported Context]
    {backported}

    [Target Code Structure]
    {target}

    Verify these aspects:
    1. Function/method signature compatibility
    2. Variable scope alignment
    3. Dependency availability
    4. Architectural consistency
    5. Control flow positioning

    YOU MUST under all circumstances, Provide your verdict strictly as a JSON object with the following keys and nothing extra:
    {{
        "location_accuracy": {{
            "structural_match": bool,
            "scope_appropriate": bool,
            "dependency_satisfied": bool
        }},
        "identified_risks": list[str],
        "suggested_adjustments": list[str],
        "placement_verdict": bool
    }}"""
    return query_model(prompt)



def verify_patch(upstream_patch, backported_patch, target_code):

    completion = client.chat.completions.create(
    model="deepseek/deepseek-chat:free",
    seed=2025,
    temperature=0,
    top_p=1,
    messages=[
        {
        "role": "user",
        "content": f'''You are an expert in verifying backported patches. Your task is to compare an upstream patch with an AI-generated backported patch and determine if the backported patch correctly applies the changes from the upstream patch to the target code, despite potential structural or syntactical differences.

    **Core Challenge**: The backported patch must achieve the same functional and security objectives as the upstream patch, even if the implementation details differ due to structural or version differences. You do not have access to the upstream source code, only the upstream patch and the target code where the backported patch is applied.

    **Inputs Description**:
    1. Upstream Patch: The original patch containing the intended changes.
    2. Backported Patch: The AI-generated patch that attempts to apply the upstream changes to the target code.
    3. Target Code: The codebase where the backported patch is applied.
    
    **Instructions**:
    1. Analyze the upstream patch to determine its intent, including:
    - Purpose (e.g., bug fix, security fix, feature addition).
    - Key logic changes or additions.
    - Modules or functions affected.
    2. Compare the backported patch against the upstream patch:
    - Verify if all key logic changes from the upstream patch are present in the backported patch.
    - Identify any structural or syntactical differences (e.g., Type-I to Type-V differences).
    - Assess whether the backported patch achieves the same objectives as the upstream patch in the target code.
    3. Provide a detailed explanation of your reasoning, including:
    - Whether the backported patch is correct or incorrect.
    - The type of differences (if any) between the upstream and backported patches.
    - Specific suggestions for fixes if the backported patch is incorrect.

    **Inputs**:
    1. Upstream Patch: {upstream_patch}
    2. Backported Patch: {backported_patch}
    3. Target Code: {target_code}

    **Output Format**:
    YOU MUST under all circumstances, Provide your verdict strictly as a JSON object with the following keys and nothing extra:
    - "is_correct": "Yes" or "No".
    - "difference_type": One of "None", "Minor", or "Major".
    - "explanation": A detailed explanation of your reasoning.
    - "suggested_fixes": Specific suggestions for fixes if the patch is incorrect (empty string if not applicable).

    **Example Output**:
    {{
    "is_correct": "Yes",
    "difference_type": "Minor",
    "explanation": "The backported patch correctly applies all key logic changes from the upstream patch. The only differences are minor syntactical adjustments due to version differences in the target code.",
    "suggested_fixes": ""
    }}


    Respond only with valid JSON. Do not write an introduction or summary.'''
        }
    ]
    )


    response_text = completion.choices[0].message.content

    # Regular expression to find JSON-like structures
    json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"  # Matches nested JSON structures

    # Find all matches (use first match if multiple JSON objects exist)
    matches = re.findall(json_pattern, response_text, re.DOTALL)

    if matches:
        json_str = matches[0]  # Take the first valid JSON block
    else:
        json_str = response_text  # Fallback to full response if no JSON is found

    print(json_str)
    
    parsed_response = json_repair.loads(json_str)
    return parsed_response


def verify_patch_2a(upstream_patch, backported_patch, target_code):

    completion = client.chat.completions.create(
    model="deepseek/deepseek-chat:free",
    seed=2025,
    temperature=0,
    top_p=1,
    messages=[
        {
        "role": "user",
        "content": f'''You are an expert in verifying backported patches. Your task is to compare an upstream patch with an AI-generated backported patch and determine if the backported patch correctly applies the changes from the upstream patch to the target code, despite potential structural or syntactical differences.

    **Core Challenge**: The backported patch must achieve the same functional and security objectives as the upstream patch, even if the implementation details differ due to structural or version differences. You do not have access to the upstream source code, only the upstream patch and the target code where the backported patch is applied.

    **Inputs Description**:
    1. Upstream Patch: The original patch containing the intended changes.
    2. Backported Patch: The AI-generated patch that attempts to apply the upstream changes to the target code.
    3. Target Code: The codebase where the backported patch is applied.
    
    **Instructions**:
    1. Analyze the upstream patch to determine its intent, including:
    - Purpose (e.g., bug fix, security fix, feature addition).
    - Key logic changes or additions.
    - Modules or functions affected.
    2. Compare the backported patch against the upstream patch:
    - Verify if all key logic changes from the upstream patch are present in the backported patch.
    - Identify any structural or syntactical differences (e.g., Type-I to Type-V differences).
    - Assess whether the backported patch achieves the same objectives as the upstream patch in the target code.
    - Pay special attention to changes that could impact functionality, security, system integrity or version control. Any deviation in these areas must be treated as a failure.
    3. Provide a detailed explanation of your reasoning, including:
    - Whether the backported patch is correct or incorrect.
    - The type of differences (if any) between the upstream and backported patches.
    - Specific suggestions for fixes if the backported patch is incorrect.

    **Inputs**:
    1. Upstream Patch: {upstream_patch}
    
    2. Backported Patch: {backported_patch}
    
    3. Target Code: {target_code}

    **Output Format**:
    YOU MUST under all circumstances, Provide your verdict strictly as a JSON object with the following keys and nothing extra:
    - "is_correct": "Yes" or "No".
    - "difference_type": One of "None", "Minor", or "Major".
    - "explanation": A detailed explanation of your reasoning.
    - "suggested_fixes": Specific suggestions for fixes if the patch is incorrect (empty string if not applicable).

    **Example Output**:
    {{
    "is_correct": "Yes",
    "difference_type": "Minor",
    "explanation": "The backported patch correctly applies all key logic changes from the upstream patch. The only differences are minor syntactical adjustments due to version differences in the target code.",
    "suggested_fixes": ""
    }}


    Respond only with valid JSON. Do not write an introduction or summary.'''
        }
    ]
    )


    response_text = completion.choices[0].message.content

    # Regular expression to find JSON-like structures
    json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"  # Matches nested JSON structures

    # Find all matches (use first match if multiple JSON objects exist)
    matches = re.findall(json_pattern, response_text, re.DOTALL)

    if matches:
        json_str = matches[0]  # Take the first valid JSON block
    else:
        json_str = response_text  # Fallback to full response if no JSON is found

    print(json_str)
    parsed_response = json_repair.loads(json_str)
    return parsed_response

def verify_patch_2b(upstream_patch, backported_patch, target_code, previous_judgment):
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat:free",
        seed=2025,
        temperature=0,
        top_p=1,
        messages=[
            {
                "role": "user",
                "content": f'''You are an expert in verifying the placement of backported patches. Your task is to ensure that the changes in the backported patch are applied in a LOGICALLY APPROPRIATE location within the target code, relative to the upstream patch and the surrounding code context.

**Previous Judgment**:
{previous_judgment}

**Core Challenge**: Even if the backported patch is functionally correct, you must verify that the changes are placed in a location that makes logical sense within the target code. This includes ensuring that the changes interact reasonably with the surrounding code and are not obviously misplaced in an unrelated or incorrect context.

**Inputs**:
1. Upstream Patch: {upstream_patch}
2. Backported Patch: {backported_patch}
3. Target Code: {target_code}

**Verification Process**:
1. Analyze the upstream patch:
   - Identify the general context of the changes (e.g., within a specific function, conditional block, loop, or class).
   - Determine the semantic purpose of the changes (e.g., fixing a validation check, modifying a data structure, or adding a security feature).

2. Analyze the backported patch:
   - Verify that the changes are placed in a logically equivalent context in the target code.
   - Check that the surrounding code structure (e.g., function calls, variable scopes, control flow) does not conflict with the intent of the upstream patch.
   - Ensure that the changes are not obviously misplaced in an unrelated or incorrect block of code.

3. Validate the placement:
   - Confirm that the changes interact reasonably with the surrounding code (e.g., variables, methods, and dependencies are properly referenced).
   - Ensure that the changes are not placed in a way that would clearly break functionality or introduce security vulnerabilities.

**Output Format**:
Respond ONLY with a JSON object containing the following keys:
{{
    "is_correct": "Yes" or "No",
    "explanation": "Brief explanation of whether the changes are placed in a logically appropriate location, including any potential issues found.",
    "suggested_fixes": "Suggestions for relocating the changes if the location is clearly incorrect (empty string if not applicable)."
}}

**Example Output**:
{{
    "is_correct": "Yes",
    "explanation": "The backported patch introduces the `NLSET` and `SPECIALSNL` sets in a logically appropriate context, and the modifications to the `_refold_parse_tree` function are placed in a reasonable location within the target code. The changes interact properly with the surrounding code.",
    "suggested_fixes": ""
}}

Respond ONLY with valid JSON. Do not include any additional commentary or explanations outside the JSON object.'''
            }
        ]
    )

    response_text = completion.choices[0].message.content

    # Regular expression to find JSON-like structures
    json_pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"  # Matches nested JSON structures

    # Find all matches (use first match if multiple JSON objects exist)
    matches = re.findall(json_pattern, response_text, re.DOTALL)

    if matches:
        json_str = matches[0]  # Take the first valid JSON block
    else:
        json_str = response_text  # Fallback to full response if no JSON is found

    print(json_str)

    parsed_response = json_repair.loads(json_str)
    print(type(parsed_response))
    return parsed_response


def extract_relevant_code(hunk, target_code):
    """
    Extracts the relevant code from the target code that is impacted by the hunk, including all meaningful context.

    Parameters:
        - hunk: The hunk from the patch file (unidiff.Hunk object).
        - target_code: The relevant code from the target file where the hunk is applied.

    Returns:
        - A string containing the relevant code impacted by the hunk, including all meaningful context.
    """
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat:free",
        seed=2025,
        temperature=0,
        top_p=1,
        messages=[
            {
                "role": "user",
                "content": f'''You are an expert in analyzing code changes. Your task is to extract the code that is useful for understanding the changes made by the hunk, including all meaningful context.

**Inputs Description**:
1. Hunk: The hunk from the patch file, containing the changes to be applied.
2. Target Code: The relevant code from the target file where the hunk is applied.

**Instructions**:
1. Analyze the hunk to identify the lines that are being added, removed, or modified.
2. Extract code from the target code that includes:
   - The lines directly impacted by the hunk.
   - All surrounding context that is meaningful for understanding the changes, such as:
     - The entire function or method where the changes are made.
     - Variable declarations or initializations used in the changed lines.
     - Control structures (e.g., loops, conditionals) that surround the changes.
     - Any related logic or calls that are affected by the changes.
3. Do not exclude any code that is meaningful for understanding the changes, even if it is not directly modified by the hunk.
4. Ensure the extracted code is complete and maintains the original formatting.

**Inputs**:
1. Hunk: {hunk}
2. Target Code: {target_code}

**Output Format**:
Return only the relevant code as a string that maintains the format found in Target Code. Do not include any additional explanations or summaries.
Respond only with the relevant code. Do not write an introduction or summary.'''
            }
        ]
    )

    response_text = completion.choices[0].message.content
    return response_text.strip()










#######THE GREAT WALL################################################################################################################################################

def compare_intent(upstream_patch, backported_patch):
    completion = client.chat.completions.create(
    model="deepseek/deepseek-r1:free",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": f"""Analyze the following upstream patch and backported patch. 
                Identify any discrepancies in intent, key logic changes, or security/functionality goals.
                Consider the upstream patch as holy, without faults and judge backported patch.
                Focus on changes made by the upstream and backported patches, some cases to consider:
                1) the changes in one may not be available in another because identical code already exists
                2) differences in functions may be due to implementation differences between versions, check if same intent is achieved despite differences
                
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
                }}"""
            }
        ]
    )
    
    print(completion)
    return parse_response(completion.choices[0].message.content)


def validate_with_context(discrepancies, backported_patch, target_code):
    completion = client.chat.completions.create(
    model="google/gemini-2.0-pro-exp-02-05:free",
    temperature=0,
    messages=[
        {
            "role": "system",
            "content": f"""You are an expert in verifying backported patches who is tasked with judging discrepancies between an upstream patch and a backported patch. 
            The target code has been abstracted to preserve only the most relevant context, such as class names, variables defined outside functions, and critical functions. 
            Non-critical functions have been abstracted to only their names, while critical functions (those essential for understanding the logic) have been preserved in full.
            Make sure you return your answer in the JSON format, as specified at the end of this prompt. 

            **Abstraction Process**:
            1. Class names and variables defined outside functions are preserved.
            2. Function names are preserved, but their implementations are abstracted unless they are critical for context.
            3. Critical functions (e.g., those containing key logic or security-related code) are kept in full.

            **Task**:
            Review the discrepancies between the upstream and backported patches. Use the abstracted target code to determine if these discrepancies are justified or problematic.

            **Input**:
            Discreprancies includes judgement from a previous expert, comparing backported and upstream patches
            - Discrepancies: {discrepancies}
            - Backported Patch: {backported_patch}
            - Abstracted Target Code: {target_code}

            **Instructions**:
            1. Differences in function names or implementations are not necessarily errors if they achieve the same intent and are part of the target codebase's design.
            1. For each discrepancy, explain if it's justified by the target code (e.g., renamed functions, version-specific syntax, or other contextual reasons).
            2. Flag any unresolved discrepancies that could impact security or functionality.
            3. Provide suggested fixes for any problematic discrepancies.

            **Output Format**:
            You MUST Follow this example format.
            Output strictly as JSON, without any extra summaries or artifacts:
            {{
                "is_correct": "No",
                "difference_type": "Major",
                "explanation": "The missing RCSID change could potentially cause maintenance issues.",
                "suggested_fixes": "Change the RCSID to match the upstream patch."
            }}
            
            Respond only with valid JSON. Do not write an introduction or summary.
            """
        }
    ]
    )
    return parse_response(completion.choices[0].message.content)


def abstract_code_context(target_code, backport_patch):
    """
    Abstract target code by preserving:
    - Class/function/variable names
    - Critical implementation logic from patch-related code
    - Control flow structures
    """
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat:free",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": f"""you are an expert at patch backporting. Process this code and patch to create focused context:
                1. Keep all class/function/variable names
                2. Keep full implementation for functions modified in the patch or for those DIRECTLY relevant to understanding the changes
                3. Abstract other functions to signatures with '# ...'
                4. Preserve control structures (if/for/try)
                5. Keep comments about intent/edge cases

                
                Backport Patch:
                {backport_patch}

                Target Code:
                {target_code}


                Output ONLY the abstracted code."""
            }
        ]
    )
    
    return completion.choices[0].message.content
