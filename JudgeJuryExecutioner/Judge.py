from prompts import COMPARE_INTENT_PROMPT, ABSTRACT_CODE_PROMPT, VALIDATE_WITH_CONTEXT_PROMPT
from parser import repair_json
from openai import OpenAI
import time

OPENROUTER_BASE_URL = "INSERT URL"
OPENROUTER_API_KEY = "INSERT API KEY"

class Judge:
    def __init__(self):
        """Initialize OpenAI client for OpenRouter"""
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

    def _call_api(self, model, prompt, temperature=0):
        """Generic API call helper"""
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            seed=2025,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def compare_intent(self, upstream_patch, backported_patch):
        prompt = COMPARE_INTENT_PROMPT.format(
            upstream_patch=upstream_patch,
            backported_patch=backported_patch
        )
        raw_response = self._call_api("deepseek/deepseek-r1:free", prompt)
        
        return repair_json(raw_response)

    def abstract_code_context(self, target_code, backport_patch):
        prompt = ABSTRACT_CODE_PROMPT.format(
            target_code=target_code,
            backport_patch=backport_patch
        )
        
        return self._call_api("deepseek/deepseek-chat:free", prompt)

    def validate_with_context(self, discrepancies, backported_patch, target_code):
        prompt = VALIDATE_WITH_CONTEXT_PROMPT.format(
            discrepancies=discrepancies,
            backported_patch=backported_patch,
            target_code=target_code
        )
        raw_response = self._call_api("google/gemini-2.0-pro-exp-02-05:free", prompt)

        return repair_json(raw_response)

    # Process function
    def process_backport(self, upstream_file, backported_file, target_code):
        discrepancies = self.compare_intent(upstream_file, backported_file)
        time.sleep(3)
        abstract_code = self.abstract_code_context(target_code, backported_file)
        time.sleep(3)
        result = self.validate_with_context(discrepancies, backported_file.path, abstract_code)
        time.sleep(3)
        
        return result
