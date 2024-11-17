from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')

def clean_search_keys(results : dict):
    filtered_dict = dict()
    for key in results.keys():
        if key not in ['search_metadata', 'search_parameters', 'search_information', 'local_map', 'inline_images', 'related_searches','dmca_messages', 'pagination', 'serpapi_pagination', 'filters', 'top_stories', 'ai_overview']:
            filtered_dict[key] = results[key]
    
    return filtered_dict

def find_subject_keys(json_response : str, user_query : str):
    llm = OpenAI()
    class Structure(BaseModel):
        relevant_keys : list[str]

    completion = llm.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": """ Provided with a user query and a JSON file as a python dictionary,
            provide the most relevant keys in the dictionary as per the query. """},
            {'role' : 'user',
            'content' : f'User query - {user_query} and dictionary response - {json_response}. Only output the relevant keys which are present in {json_response}.'}
        ],
        response_format=Structure,
    )

    event = completion.choices[0].message.parsed
    return event.relevant_keys
