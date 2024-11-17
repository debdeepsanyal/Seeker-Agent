import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from serpapi import GoogleSearch
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from langgraph.graph.state import CompiledStateGraph
from utils import clean_search_keys, find_subject_keys
load_dotenv(dotenv_path='.env')

serpapi_key = os.environ['SERPAPI_API_KEY']
openai_key = os.environ['OPENAI_API_KEY']

class State(TypedDict):
    query : Optional[str]
    modified_query : Optional[str]
    search_results : Optional[dict]
    response_list : Optional[List[str]]
    gather_llm_response : Optional[str]
    subject_keys : Optional[List[str]]
    counter : Optional[int]
    final_response : Optional[dict]

class SearchAgent:
    def __init__(self, column_elements : List[str]):
        self.llm = OpenAI()
        self.column_elements = column_elements
        self.loop_count = 0
        self.graph = self._create_graph()
    
    
    def _create_graph(self) -> CompiledStateGraph:
        graph = StateGraph(State)
        graph.add_node('modify_query', self._modify_query_node)
        graph.add_node('search', self._search_node)
        graph.add_node('find_llm', self._find_llm_node)
        graph.add_node('gather_llm', self._gather_llm_node)
        graph.add_node('format_llm', self._format_llm_node)
        graph.set_entry_point("modify_query")
        graph.add_edge('modify_query', 'search')
        graph.add_edge('search', 'find_llm')
        graph.add_conditional_edges('find_llm',  lambda state : 'gather_llm' if state['counter'] >= len(self.column_elements) else 'search')
        graph.add_edge('gather_llm','format_llm')
        graph.add_edge('format_llm', END)
        return graph.compile()

    def _modify_query_node(self, state : State):
        print('\033[1m\033[3m\033[36mEntering Modify Query Node...\033[0m')
        initial_element = self.column_elements[0]
        self.user_query = user_query = state['query']
        if self.user_query.find('{') != -1:
            user_query = user_query[ : user_query.find('{')] + initial_element + user_query[user_query.find('}') + 1 : ]
        
        state['counter'] = 0
        state['response_list'] = []
        completion = self.llm.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": """You are a helpful assistant, and provided a user query which is meant for a google search, 
                you need to restructure the query to include a broader, more inclusive set of search results. Analyse the original query and 
                add clarifications to the generated query if needed. Include all relevant keywords in the generated query, ensuring that the generated query is optimized for Google search.
                For product search based queries, do not suggest any specific company for it might limit the search results instead of broadening them."""},
                {
                    "role": "user",
                    "content": f"""Find me the customer service emails for the following companies - Meta?"""
                },
                {
                    "role": "assistant",
                    "content": f"""The user is asking for a customer service email, which means that they are probably looking for a way
                    to connect to the companies to query them of some grievances, hence they should be provided with as many options which help them 
                    avail to customer services of the company. The query should be modified in order to accomodate customer service/helpdesk numbers, 
                    any portal leading to help, etc., along with the requested customer service email.
                    
                    `Modified Search:`
                    Find me the Meta customer service email, Meta customer service number, Meta helpdesk number."""
                },
                {
                    "role": "user",
                    "content": f"""Find me the best place near me from where i can get a pizza?"""
                },
                {
                    "role": "assistant",
                    "content": f"""The user is asking for a nearby place which is offering pizzas. For this, we might consider all sorts of eateries from Google maps
                    which are currently open at this hour. This can include pizzerias, restaurants, food trucks, and delivery services, along with reviews or ratings from sources like Google, Yelp, and TripAdvisor.
                    
                    `Modified Search:`
                    Find me the best places near me on Google maps where I can get pizza, including pizzerias, restaurants, food trucks, and delivery services which are currently open, along with reviews or ratings from sources like Google, Yelp, and TripAdvisor."""
                },
                {
                    "role": "user",
                    "content": user_query
                },
            ],
        )

        state['modified_query'] = completion.choices[0].message.content
        return state 
    
    def _search_node(self, state : State):
        print(f'\033[1m\033[3m\033[36mEntering Search Node... {self.loop_count + 1}/{len(self.column_elements)}\033[0m')
        if self.loop_count != 0:
            state['modified_query'] = state['modified_query'].replace(self.column_elements[self.loop_count - 1], self.column_elements[self.loop_count])
        else:
            state['modified_query'] = state['modified_query'][state['modified_query'].find('Modified Search') + 18 : ]    

        self.loop_count += 1
        state['counter'] += 1
        params = {
            "q": state['modified_query'],
            "hl": "en",
            "gl": "us",
            "google_domain": "google.com",
            "api_key": serpapi_key
        }

        search = GoogleSearch(params)
        state['search_results'] = search.get_dict()
        return state 

    def _find_llm_node(self, state : State):
        print('\033[1m\033[3m\033[36mEntering Find LLM Node...\033[0m')
        search_query = state['modified_query']
        state['search_results'] = clean_search_keys(state['search_results'])
        completion = self.llm.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": """You are a helpful assistant, and given a python dictionary 
                containing google search results for a certain query, your task is to obtain the most relevant informations regarding
                the user query from the provided python dictionary."""},
                {
                    "role": "user",
                    "content": f"""Provided the user query - {search_query}, here is the google search results for the query - `results` - \n {state['search_results']}.
                    Analyse all the keys and their values from the results, and extract out the most relevant informations from the provided `results` which best satisfies the user query {search_query}. 
                    If you are unable to find any direct information which satisfies the user query, search for any additional information, including helpful links, which might be relevant.
                    For a reference, here is the user query again - {search_query}, and here is search results - \n {state['search_results']}"""
                }
            ],
        )

        normal_response = completion.choices[0].message.content
        state['response_list'].append(normal_response)
        return state 
    
    def _gather_llm_node(self, state : State):
        print('\033[1m\033[3m\033[36mEntering Gather LLM Node...\033[0m')
        assert len(state['response_list']) == len(self.column_elements)
        completion = self.llm.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": """You are a helpful assistant, and given a list of information, your job
                is to analyse each of the informations in the list, and find out the common data from each information
                information in the list and return them in the form of a list."""},
                {
                    "role": "user",
                    "content": """Provided the user query - \n "Find me the email and address of the headquarters for the company - {company}." , here is the list of information gathered for the same query 
                    on various subjects - 

                    ["To address the user query effectively using the provided `results`, we need to extract the keys that contain relevant information about Google's headquarters, including details about international offices and corporate contact information. Let's consolidate this information:\n\n1. **Google Headquarters Information**:\n   - **Address**: The headquarters are located at 1600 Amphitheatre Parkway, Mountain View, CA 94043, USA.\n   - **Phone Number**: You can contact the headquarters at (650) 253-0000.\n   - **Source**: This information is corroborated by multiple sources such as 'About Google' and 'corporate-office-headquarters.com'.\n\n2. **Corporate Contact Information**:\n   - **General Contact Number**: Another number for customer services available is 1-866-246-6453, which operates Monday through Friday from 9 am to 8 pm ET.\n   - **Source for Customer Support**: This is mentioned on 'PissedConsumer'.\n\n3. **International Office Details**:\n   - Google operates more than 70 offices in over 50 countries, as mentioned on 'About Google', which provides a directory of locations around the world. \n   - **Link for Locations**: More information can be found at [Google Office Locations](https://about.google/intl/ALL_us/locations/).\n\n4. **Email and Additional Support**:\n   - While specific email addresses are not provided in the search results, Google Workspace and general inquiries can be reached through [Google Cloud Contact Page](https://cloud.google.com/contact), where phone, email, and chat support are available.\n\n5. **Helpful Links**:\n   - For a broader understanding and access to more detailed contacts and office specifics, visiting [Contact Google](https://about.google/intl/ALL_us/contact-google/) is suggested.\n\nThese elements from the search results cover the primary requirements of the user query by providing the address, phone numbers, and further usability links related to Google’s headquarters and international offices.",
                    'Here are the most relevant pieces of information gathered from the provided search results for Meta\'s headquarters contact information:\n\n1. **Physical Address**: The physical address for Meta\'s headquarters is "1 Hacker Way, Menlo Park, CA 94025-1456". This information is found in the snippet for the Better Business Bureau\'s profile on Meta Technology Company.\n\n2. **Contact Page**: \n   - The most likely official contact page can be found via the "About Meta" page, which was linked as "Offices - Meta" [about.meta.com/media-gallery/offices-around-the-world](https://about.meta.com/media-gallery/offices-around-the-world/). Although this doesn\'t explicitly list contact information, it likely allows navigation to further contact details or resources.\n   - Additionally, the Facebook Help Center page [facebook.com/help](https://www.facebook.com/help) could provide further means of assistance or contacting Meta.\n\n3. **Email Address and Phone Number**: The search results do not directly list an email address or phone number for Meta\'s headquarters. However, contacting customer service for Meta-related inquiries could be facilitated via the general Facebook customer service page as suggested by the "Facebook Customer Service Contacts" found [here](https://www.elliott.org/company-contacts/facebook/). This page mentions reaching out via phone, email, or social media, but specific contact details aren\'t provided in the snippet.\n\n4. **Additional Resources**: \n   - The Meta Investor Resources page [investor.fb.com/resources](https://investor.fb.com/resources/default.aspx) could offer further means of contacting Meta for investor-related inquiries and might provide further contact methods if necessary.\n\nFor more precise contact details such as a direct email or phone number, it\'s often best to consult these official pages or consider reaching out through the provided channels to request further specific information.',
                    "Based on the provided search results, the most relevant information for Amazon's headquarters contact details is as follows:\n\n1. **Physical Address:**\n   - Amazon's headquarters is located at **410 Terry Ave. North, Seattle, WA, 98109-5210**. This information is mentioned in the snippet from the first search result in corporate-office-headquarters.com.\n   - Another address mentioned is **325 9th Ave. N. Seattle, WA 98109-5210**, found in the Amazon.com business notice procedures.\n   - Additionally, a separate source provides the address as **202 Westlake Ave N Ste 2, Seattle, WA 98109-5264**, according to Better Business Bureau.\n\n2. **Phone Numbers:**\n   - The main corporate phone number listed is **(206) 266-1000**.\n   - For Amazon Customer Service, the phone number is **1-888-280-4331** for US customers, and there is an international contact number, **+1 (206) 922-0880**.\n\n3. **Email Address:**\n   - The email provided for escalations in customer service is **cs-escalations@amazon.com**, as mentioned in the Elliott Report.\n   - For investor relations, the email is **amazon-ir@amazon.com**.\n\n4. **Official Contact Page:**\n   - The official Amazon contact page for customer service can be found at [Amazon Help & Customer Service](https://www.amazon.com/gp/help/customer/display.html).\n   - For investor relations, the contact page is [Amazon Investor Relations Contact Page](https://ir.aboutamazon.com/contact-us-and-request-documents/default.aspx).\n\nThese are the key contact points and addresses available from the search results that align with the user query about Amazon's headquarters."]
                    
                    .Analyse each data in the provided list very carefully, and compare them 
                    against the provided user query to find a common set of information relevant to the user query, across all the data present 
                    in the list."""
                },
                {
                    "role" : "assistant",
                    "content" : """First, we need to identify the main subjects present in the user query for which we should be looking out for.
                    The user is asking for the email and address of the headquarters of the company, so these are the two pieces of information I should be looking for in the list of information present.
                    
                    From the first data in the list, which is about the company `Google`, we have the direct information about the address of the headquarters, 
                    which is mentioned as `1600 Amphitheatre Parkway, Mountain View, CA 94043, USA.`
                    As for the email, although specific information is not present, we do find relevant contact informations like [Google Cloud Contact Page](https://cloud.google.com/contact) and [Contact Google](https://about.google/intl/ALL_us/contact-google/).
                    Apart from this, a few phone numbers have been provided, but since there isn't a direct mention of phone numbers in the user_query, we will ignore them for now.
                    
                    From the next data in the list, which is about the company `Meta`, we again have direct information on the address of the headquarters as mentioned in the user query, 
                    which is `1 Hacker Way, Menlo Park, CA 94025-1456`. As for the email, we don't find any dedicated email addresses but we do find helpful contact information like [facebook.com/help](https://www.facebook.com/help), (https://www.elliott.org/company-contacts/facebook/) and (https://investor.fb.com/resources/default.aspx).
                    We do not find any other information from this data which is relevant to the user query. 
                    
                    From the last data in the list, which is about the company `Amazon`, a few addresses are mentioned, but we observe that the address `410 Terry Ave. North, Seattle, WA, 98109-5210` was mentioned in the first search result, hence we will go with this one. 
                    As for the email, we find a couple of email addresses at - cs-escalations@amazon.com and amazon-ir@amazon.com. Some other helpful links, as we found in the data for the prior companies, include - [Amazon Help & Customer Service](https://www.amazon.com/gp/help/customer/display.html). 
                    
                    Hence, having collected all the informations from the data present, we can format them as follows - 
                    
                    
                    {
                        "Address" : ["1600 Amphitheatre Parkway, Mountain View, CA 94043, USA.", "1 Hacker Way, Menlo Park, CA 94025-1456", "410 Terry Ave. North, Seattle, WA, 98109-5210"],
                        "Email" : ["https://cloud.google.com/contact, https://about.google/intl/ALL_us/contact-google/", "https://www.facebook.com/help, https://www.elliott.org/company-contacts/facebook/, https://investor.fb.com/resources/default.aspx", "cs-escalations@amazon.com, amazon-ir@amazon.com"]
                    }

                    """
                },
                {
                    "role" : "user",
                    "content" : f"Here is the user query - {self.user_query}, and here is the list of data - {state['response_list']}"
                }
                
            ],
        )

        state['gather_llm_response'] = completion.choices[0].message.content
        return state 
    
    def _format_llm_node(self, state : State):
        print('\033[1m\033[3m\033[36mEntering Format LLM Node...\033[0m')
        completion = self.llm.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": """You are a helpful assistant, and given a response, your task 
                is to format the response in a json format. """},
                {
                    "role": "user",
                    "content": f"""Provided the user query - \n {self.user_query} and the relevant information about the query as - 
                    {state['gather_llm_response']}, structure the informations relevant to the query present in the response in a JSON format. 
                    """
                },
            ],
            response_format = { "type": "json_object" }
        )

        json_response = completion.choices[0].message.content
        json_dict = json.loads(json_response)#json_dict is a dictionary with a single key, the value of which is a list of dictionaries, each dictionary in the list corresponding to each item in self.column_elements
        keylist = [key for key in json_dict.keys()]
        flag = 0
        if len(keylist) == len(self.column_elements) and all(keylist[i] == self.column_elements[i] for i in range(len(keylist))):
            information_list = json_dict
        else:    
            primary_key = keylist[0]
            information_list = json_dict[primary_key] #this is a list of dictionaries 
            flag = 1
        #we want to return a dictionary where every key is a subject, and the value to the key is a list of retrieved information (they'll be in order)
        state['subject_keys'] = find_subject_keys(json_response, self.user_query)
        state["final_response"] = dict()
        for key in state["subject_keys"]:
            state['final_response'][key] = []

        print(f'JSON dict - {json_dict}')
        print('----------------------------------------------------')
        print(f'Response List - {state["response_list"]}')
        print('----------------------------------------------------')
        print(f'Gather LLM Response - {state['gather_llm_response']}')
        print('----------------------------------------------------')
        print(f'Information key - {information_list}')
        print('----------------------------------------------------')
        print(f'Subject keys - {state['subject_keys']}')
        print('----------------------------------------------------')
        if flag:
            for data in information_list:
                print(f'Info list element as `data` - {data}')
                print('---------------------------------------')
                for key in state["subject_keys"]:
                    if key in data:
                        state['final_response'][key].append(data[key])
                    else:
                        state['final_response'][key].append('')
        else:
            for data in information_list:
                info = information_list[data]
                for key in state["subject_keys"]:
                    if key in info:
                        if isinstance(info[key], list):
                            hold = str(info[key])[1:-1]
                        else:
                            hold = info[key]
                        state['final_response'][key].append(hold)
                    else:
                        state['final_response'][key].append('')                        
        
        return state 

    def invoke(self, user_query : str):
        final_state = self.graph.invoke({'query' : user_query})
        return final_state['final_response']
        
        
