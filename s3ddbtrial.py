import spacy
import boto3
from boto3.dynamodb.conditions import Attr
import json
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
    "KR": ["yonhapnews.co.kr", "koreatimes.co.kr"]
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

def push_to_S3(json_file, topic):

    bucket_name='newssummariesagentprojectdl'
    object_key= topic + '.json'
    print(object_key)
    content=json_file

    s3.put_object(Bucket=bucket_name, Key=object_key, Body=content)
    return

# image generation add thumbnail if it fits text
# def thumbnailgen(response_eng):
    #return image
query='what is testing worth?'
keylist = ['test','for','DB','interaction']
response='everything'
topic= "_".join(keylist)
## will be really long but needs to be higher chance of not exact match because otehrvise response will be replaced in S3
print(topic)

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

keys=keylist
s3_key=topic + '.json'
table.put_item(
    Item={
        "Keywords": keys,
        "S3Key": s3_key,
        'PromptLanguage': 'en',
        'Date': '2002'
    }
)

print(response)
print(s3_key)

### one benefit we create smal
