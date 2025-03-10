import re
import json
from openai import OpenAI
import json_repair


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="INSERT API KEY",
    )


def query_model(prompt):
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat:free",
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

    # Find all matches (use first match if multiple JSON objects exist)
    matches = re.findall(json_pattern, response, re.DOTALL)

    if matches:
        json_str = matches[0]  # Take the first valid JSON block
    else:
        json_str = response  # Fallback to full response if no JSON is found

    # print(json_str)
    
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

