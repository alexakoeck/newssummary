#imports
import spacy
import boto3
from boto3.dynamodb.conditions import Attr
import json
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import warnings
warnings.simplefilter(action='ignore',category=FutureWarning)
from langchain_google_genai import GoogleGenerativeAI
from langchain.agents import initialize_agent, Tool
#from langchain.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate

#region detection
from langdetect import detect

REGIONAL_SITES = {
    "GB": ["bbc.com", "theguardian.com"],
    "DE": ["sueddeutsche.de", "zeit.de", "tagesschau.de"],
    "KR": ["www.chosun.com","chosun.com/english", "koreatimes.co.kr"]
}

LANG_TO_REGION = {
    "en": "GB",
    "de": "DE",
    "ko": "KR"
}

##websearch
from langchain_community.tools import BraveSearch
from langchain.agents import initialize_agent, Tool
#from langchain.chat_models import ChatOpenAI
#from langchain.tools.tavily_search import TavilySearchResults
import ast
import re
import requests
from newspaper import Article
from langchain_community.utilities import GoogleSerperAPIWrapper
import os

translate = boto3.client('translate', region_name='us-west-2')
s3= boto3.client('s3', region_name='us-west-2')
comprehend = boto3.client('comprehend',  region_name='us-west-2')
dynamodb= boto3.resource('dynamodb', region_name='us-west-2')
table_name='Keywords'
table=dynamodb.Table(table_name)

#import tool functions
from ToolsFile import push_to_S3, detect_language_region, detect_topic_region_llm, get_news_sources, search_web, search_articles, translate_prompt, translate_articles, merge

def final(input):
    query = input

#step 1 set up Gemini_API
##set keys in environment variables
    GOOGLE_API_KEY = "AIzaSyBYT_gvrgceKBEl5-2X5lu5k0s9NS2iV-A"

    llm = GoogleGenerativeAI(
        model="gemini-2.0-flash", ##test gemini-pro maybe better model available in AWS!!
        google_api_key=GOOGLE_API_KEY
    )

#step 2 extarct user prompt language for later or if requested language
#if language of choice is not specified give language of inital prompt
    try:
        prompt_l=f"What language is used in this prompt? reply with only a 2-letter lowercase ISO 639-1 language code (like 'en', 'de', 'ko').\n\nQuery: {query}"
        response= llm.invoke(prompt_l)
        prompt_lang = code = response.strip().lower() if isinstance(response, str) else response.content.strip().lower()

    except:
        prompt_lang = "en"

#step 3 propmt ##no matetr prompt language this works best in english
#grab query
##add COT
    example_prompt = PromptTemplate.from_template('Input:"{newsrequest}"\nResponse: {response}"\nSources: {sources}')

    examples = [
        { "newsrequest": "Was sind die neusten nachrichten zu Friedrich Merz?", "response": "Friedrich Merz, CDU-Vorsitzender, führt derzeit intensive Koalitionsverhandlungen mit der SPD zur Bildung einer neuen Bundesregierung nach der Bundestagswahl. Zentrale Themen sind Migration, Sicherheitspolitik und wirtschaftliche Investitionen. Merz fordert schnelle Entscheidungen und einen klaren Kurswechsel in der Haushaltspolitik. Im Fokus steht die geplante Lockerung der Schuldenbremse, um Investitionen in Verteidigung und Infrastruktur zu ermöglichen. Dies stößt jedoch auf Kritik innerhalb der Union. Merz fordert zusätzlich einen 'Kassensturz' und die Überprüfung von Sozialausgaben. Trotz parteiinterner Spannungen zeigt er sich optimistisch, bis Ostern eine stabile Regierungsbildung zu erreichen.", "sources": "tagesschau.de, welt.de, zeit.de" },
        { "newsrequest": "What are the newest news about german political situation?", "response": "Germany is in the midst of coalition negotiations between the CDU/CSU and the SPD following the federal election. CDU leader Friedrich Merz is aiming to form a new government. Key issues in the talks include migration policy, where the CDU/CSU supports stricter border measures, while the SPD warns of potential EU law violations. Economic discussions center around a proposed €500 billion special fund for defense and infrastructure, which would require constitutional amendments. Welfare reform is another contentious point, with debates over the future of the citizen's income program. Meanwhile, the Federal Constitutional Court has rejected legal complaints from the Bündnis Sahra Wagenknecht concerning electoral law.", "sources": "tagesschau.de, zeit.de, welt.de" },
        { "newsrequest": "I want to know about what is hapening with the election in south korea.", "response": "As of June 3, 2025, South Korea is holding a snap presidential election following the impeachment of President Yoon Suk-yeol over his declaration of martial law in late 2024. Voter turnout surpassed 70% by late afternoon, reflecting high public engagement. The main candidates are Lee Jae-myung (Democratic Party), who campaigns on economic reform and social equity, and Kim Moon-soo (People Power Party), advocating conservative policies. The election is widely seen as a turning point to restore democratic stability, with the new president expected to take office immediately.", "sources":"koreaherald.com, koreatimes.co.kr" },
        { "newsrequest": "What happened on last friday in the UK.", "response": "On Friday, 30 May 2025, the UK saw important political and policy updates. Chancellor Rachel Reeves announced billions in new capital investments for regions outside southeast England, revising the Treasury’s “green book” rules to address regional inequality. She also nominated Richard Hughes for a second term as chair of the Office for Budget Responsibility, ensuring continuity in fiscal oversight. The government faced criticism over a £1.6 billion trade deal with Gulf states lacking human and animal rights protections. Proposed welfare reforms sparked concern from Labour MPs and charities about potential increases in homelessness and poverty. The NHS was under pressure due to delays in ADHD assessments, highlighting challenges in mental health services. Energy regulator Ofgem fined three gas firms £8 million for poor emergency response times. On the royal front, the Princess Royal attended the Caribbean-Canada Leaders Dialogue and The King’s Birthday Party Reception in Barbados, while the Duke of Kent visited cultural sites in Scotland. The European Darts Open 2025 also began in Germany, though several top players, including world number one Luke Humphries, withdrew.", "sources": "theguardian.com, thetimes.co.uk, thesun.co.uk "},
        { "newsrequest": "대통령 선거는 어떻게 진행되고 있나요?", "response": "오늘(6월 3일)은 제21대 대통령 선거 본투표일로, 전국 1만 4천여 투표소에서 오전 6시부터 오후 8시까지 투표가 진행되고 있습니다. 이번 대선은 조기대선 성격으로 치러지며, 각 후보와 정당은 높은 투표율이 자신들에게 유리하다고 주장하며 투표 참여를 독려하고 있습니다. 사전투표와 재외투표 결과가 오늘 투표와 합산되어 당선자가 결정되며, 개표는 투표 종료 직후 시작되어 자정 무렵 당선인 윤곽이 드러날 것으로 예상됩니다. 최종 당선 확정은 내일(4일) 오전 6~9시 사이로 전망됩니다. 이번 선거는 투표율이 역대 대선과 비교해 높은 편이며, 80%에 육박할 수 있다는 관측도 나옵니다. 이재명(더불어민주당), 김문수(국민의힘), 이준석(개혁신당) 등 주요 후보들은 자택에서 개표 결과를 지켜보고 있습니다. 각 당은 높은 투표율이 자신들에게 유리하다고 해석하고 있으며, 부동층 표심이 최대 변수로 꼽히고 있습니다.", "sources": "weekly.choson.com, yna.co.kr"},
    ]

    prompt = FewShotPromptTemplate(
        examples=examples,
        example_prompt=example_prompt,
        prefix="""You are a new-summarization Agent that summarizes events related to the prompt using articles from reliable websites as well as safed summaries of your previous examples in combination.
            You should do so in an unbiased manner and answer in the language of the request.
            The summary should be short and readyable within 2 minutes.

            For each input query, follow these reasoning steps:
            1. you need to detect the region boud to topics in the promt (use 'FindRegion' Tool)
            2. Find websites using FindAdditionalWebsites: Identify reliable websites using the FindRegion or FindAdditionalWebsites tools only.
            3. Retrieve relevant and available (working URL) news articles from web and your databases matching the prompts only from the previously defined websites
            4. Sometimes you want to match the language of the articles for better summarization
            5. if still too long Summarize the information from all selected articles in a clear, factual, and concise manner using the same language as the query.
            6. Provide the short summary and sources of the information in the prompt language readable in 2 minutes.

            after each step you should evaluate and if the results are not sufficient repeat some steps.

            Use the following examples as guidance:""",

        suffix='Input: "{input}"\nResponse:\nSources',
        input_variables=["input"],
        )

#step 4 agent
    tools1=[
        Tool(
            name='FindRegion' ,
            func=get_news_sources,
            description='this tool is the initial tool to detect the region boud to the topics of the prompt and choose the reliable websites we can search from news on'
    ),
        Tool(
            name='AddtitionalWebsites',
            func=search_web,
            description='this is useful for searching the web fro reiable and unbiased news sources if the FindWebsites tool does not work and returns emty list'
    ),
        Tool(
            name='NewsArticleSearch',
            func=search_articles,
            description='input needs :  websites, query and the prompt_lang code separated by comma not in a full string  more like a dictionary. this tool is for article retrival and lets you search for previous responses matching the prompt and new articles from predefined websites.'
    ),
        Tool(
            name='TranslateArticles',
            func=translate_articles,
            description='this tool can help you fro precise translation of the retrieverd articles if you want to match their language for summarization.'
    ),
        Tool(
            name='TranslatePrompt',
            func=translate_prompt,
            description='This allows you to translate the prompt into the region language or another language.'
    ),
        Tool(
            name='ArticleSummarization',
            func=merge,
            description='this tool merges the articles to a clear and comprehensive summary')
    ]
 # Tool(name='GetPrevResults',func=extract_s3summaries,description='')

    agent=initialize_agent(
        tools=tools1,
        llm=llm,
        agent="zero-shot-react-description", ##best option for none chat agent
        handle_parsing_errors=True,
        return_intermediate_steps=True, 
        verbose=True ##in application do not want to show all reasoning steps activate for tests
    )


    response=agent.invoke(prompt.format(input = query))['output'] ##only response text
    #print(response)  ##for checking

# either have saved or detect response language and check if output matches othervise translate


    #print('test1')
# Load the English model
    nlp = spacy.load("en_core_web_sm")
# Process the text
    doc = nlp(response)

# Extract named entities
    entities = [(ent.text, ent.label_) for ent in doc.ents]
# Optionally filter by entity types
    important_types = {"PERSON", "ORG", "GPE","LOC"} ##not date
    keylist = [ent.text for ent in doc.ents if ent.label_ in important_types]

    topic= "_".join(keylist)
## will be really long but needs to be higher chance of not exact match because otehrvise response will be replaced in S3

#create json
    data={
        "prompt": query,
        "summary": response #,
    #"thumbnail": thumbnail,
    #"region": region
    }
    print(data)
    json_file=json.dumps(data)
    push_to_S3(json_file,topic)



#put keywords and s3 key to dynamo db for rag


    current_time = datetime.now()
    time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

    keys=keylist
    s3_key=f'{topic}.json'
    table.put_item(
        Item={
            "Keywords": keys,
            "S3Key": s3_key,
            'PromptLanguage': prompt_lang,
            'Date': time_str
        }
    )

    return response

### one benefit we create small but easy understandable news sumamrization archive sorted by prompt,region and topic,

