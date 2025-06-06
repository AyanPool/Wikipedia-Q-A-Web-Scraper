# -*- coding: utf-8 -*-
"""webscraper.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/19WOf2FWenOHvaq_Gxe9xKCwgHSBRs0RP

#Requirements
"""

# pip install wikipedia-api
# pip install sentence-transformers 
# pip install requests 
# pip install flask
# pip install nltk
# pip install google-generativeai
# pip install google.generativeai


"""#Importing Libraries"""

import os
import re
import wikipediaapi
import numpy as np
import requests
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline, AutoTokenizer, AutoModelForQuestionAnswering
import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize
from flask import Flask, request, jsonify
import asyncio

"""#Webscraping the wiki page and getting the chunks"""

user_agent = "MyWikiScraper/1.0 (https://example.com/my-wiki-scraper)"
wiki_wiki = wikipediaapi.Wikipedia( user_agent=user_agent)

def fetch_wikipedia_page(url):
    page_title = url.split("/")[-1]
    page = wiki_wiki.page(page_title)
    if not page.exists():
        raise ValueError(f"Page '{page_title}' does not exist.")
    return page.text

url = 'https://en.wikipedia.org/wiki/Luke_Skywalker'
content = fetch_wikipedia_page(url)

def chunk_text(text, chunk_size=512):
    words = word_tokenize(text)
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

def select_relevant_chunks(text, question, model, num_chunks=3, chunk_size=1024):
    chunks = chunk_text(text, chunk_size)
    question_embedding = model.encode(question, convert_to_tensor=True)
    chunk_embeddings = [model.encode(chunk, convert_to_tensor=True) for chunk in chunks]
    similarities = [util.pytorch_cos_sim(question_embedding, chunk_embedding)[0][0].item() for chunk_embedding in chunk_embeddings]
    relevant_indices = np.argsort(similarities)[-num_chunks:]
    relevant_chunks = [chunks[i].strip() for i in relevant_indices]
    return relevant_chunks

embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

"""#Question answering- BERT (first try)

"""

# qa_model_name = "bert-large-uncased-whole-word-masking-finetuned-squad"
# tokenizer = AutoTokenizer.from_pretrained(qa_model_name)
# qa_model = AutoModelForQuestionAnswering.from_pretrained(qa_model_name)
# qa_pipeline = pipeline("question-answering", model=qa_model, tokenizer=tokenizer)

# answer = qa_pipeline(question=question, context=context)
# print("Answer:", answer['answer'])

# context

"""#Question answering- Gemini (Second try -> used)"""

# copy and paste your API key inside the quotes
GEMINI_API_KEY= "AIzaSyBejCN1RQ8180i6-yydPJeCs05r4Hnaj4c"


import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)

# Set up the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 0,
  "max_output_tokens": 8192,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]

model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)

convo = model.start_chat(history=[])

def gemini_output(Prompt):
  convo.send_message(Prompt)
  print(convo.last.text)
  return convo.last.text

def answer_query(query):
  question = query
  relevant_chunks = select_relevant_chunks(content, question, embedding_model)
  context = " ".join(relevant_chunks)
  Prompt= (f"The context is {context}, The question is {question}, Give me the most relevant answer.")
  return gemini_output(Prompt)

from flask import Flask, request, jsonify

app = Flask(__name__)

class WrapperAPI:

  def process_query(self, query):
    # Call your original function and handle the response
    answer = answer_query(query)
    # You can modify or format the answer here
    return answer

@app.route('/', methods=['POST'])
def answer_user_query():
  # Get the query from the request body
  data = request.get_json()
  if 'query' not in data:
    return jsonify({'error': 'Missing query parameter'}), 400
  query = data['query']

  # Create an instance of the wrapper
  wrapper = WrapperAPI()
  # Call the process_query function and return the answer
  answer = wrapper.process_query(query)
  return jsonify({'answer': answer})

if __name__ == '__main__':
  app.run(debug=True)
