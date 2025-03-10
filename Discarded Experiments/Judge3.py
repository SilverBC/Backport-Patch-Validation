from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
import json
from prompts import compare_intent_prompt, abstract_code_prompt, validate_with_context_prompt
from parser4 import repair_json
import openai

API_KEY = "INSERT API KEY"
openai.api_key = API_KEY

class Judge:
    def __init__(self):
        """Initialize LLMs and chains."""
        self.deepseek_model = ChatOpenAI(
            model_name="deepseek/deepseek-chat:free",
            temperature=0,
            openai_api_key=API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        self.deepseek_r1_model = ChatOpenAI(
            model_name="deepseek/deepseek-r1:free",
            temperature=0,
            openai_api_key=API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        self.gemini_model = ChatOpenAI(
            model_name="google/gemini-2.0-pro-exp-02-05:free",
            temperature=0,
            openai_api_key=API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        

    def compare_intent(self, upstream_patch, backported_patch):
        chain = compare_intent_prompt | self.deepseek_r1_model | JsonOutputParser()
        raw_json_result = chain.invoke({"upstream_patch":upstream_patch, "backported_patch":backported_patch })
        
        return raw_json_result

    def abstract_code_context(self, target_code, backport_patch):
        chain = abstract_code_prompt | self.deepseek_model
        result = chain.invoke({"target_code": target_code, "backport_patch": backport_patch})
        
        return result

    def validate_with_context(self, discrepancies, backported_patch, target_code):
        chain = validate_with_context_prompt | self.gemini_model | JsonOutputParser()
        raw_json_result = chain.invoke({"discrepancies": discrepancies, "backported_patch": backported_patch, "target_code": target_code})
        
        return raw_json_result

    # Process function
    def process_backport(self, upstream_file, backported_file, target_code):
        discrepancies = self.compare_intent(upstream_file, backported_file)
        abstract_code = self.abstract_code_context(target_code, backported_file)
        result = self.validate_with_context(discrepancies, backported_file.path, abstract_code)
        
        return result
