"""
Provides high-level functions for running tasks on LLMs
"""

from ollama import Client
import json


# HOST = '192.168.100.47'
HOST = '10.0.0.5'
# HOST = 'localhost'

client = Client(
    host=f'http://{HOST}:11434'
)

FAST_MODEL = 'gemma3n:e4b'
COLLATE_MODEL = 'gemma3:27b'


def parse_stream(stream, verbose=True):
    if verbose: print('\nvvvvv live llm output vvvvv')
    response = ""
    for chunk in stream:
        chunk = chunk.message.content
        response += chunk
        if verbose: print(chunk, end='', flush=True)
        if "</think>" in response: # wait for the model to stop thinking
            if len(response) > 300 and response[-100:] in response[-300:-100]: # stop if the model repeats itself 
                if verbose: print('[BREAK]')
                os.system(f'OLLAMA_HOST={HOST} ollama stop {model}')
                break

    response = response.split("</think>")[-1].strip()

    if verbose: print('\n^^^^^ live llm output ^^^^^\n\n')

    return response

def generate_search_query(question):
    prompt = f"""The user will give you a question and your task is to turn it into a fitting web search query. Don't overcomplicate it. Write only the query and not anything else. Don't make the query too specific."""

    messages = [
        {
            'role': 'system',
            'content': prompt
        },
        {
            'role': 'user',
            'content': 'How far is the Earth from the sun?'
        },
        {
            'role': 'assistant',
            'content': 'distance from earth to sun'
        },
        {
            'role': 'user',
            'content': question
        }
    ]

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )
    
    return parse_stream(stream)
    

def read_page_and_evaluate(text, question):
    """
    Reads and summarizes text, extracting information relevant to 
    the question. Then determines whether the text contains any 
    answer to the question.
    """

    # Summarize
    prompt = f"""You will be given a text from a web page and your job is to summarize the text. You will also be given a question from the user. You should only extract the information from the given text that is relevant to the question. Don't just say what's in the text - write the actual points inside the text. In your summary you're not supposed to include any information that isn't related to the question. Don't mention any further reading or sources. Limit your answer to 300 words unless you need more words to capture the point."""

    messages = [
        {
            'role': 'system',
            'content': prompt
        },
        {
            'role': 'user',
            'content': question
        },
        {
            'role': 'system',
            'content': f"""Use the following text to answer the question from the user. If the answer isn't included in the text, then say you the source doesn't contain the information. Don't bring up any information you know, only summarize what's in the following text to answer the question.\n\n<source_text>\n{text}\n</source_text>"""
        }
    ]

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )
    
    summary = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': summary
    })

    # Evaluate

    messages.append({
        'role': 'user',
        'content': f"""Does the summary you created contain an answer or relevant information to the original question "{question}"?"""
    })

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )

    assistant = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': assistant
    })

    messages.append({
        'role': 'user',
        'content': f"""If your summary contains an answer or revelant information to the original question, then write YES otherwise write NO. Don't write anything else besides YES or NO"""
    })

    for retry in range(3):
        stream = client.chat(
            model=FAST_MODEL, 
            messages=messages,
            stream=True
        )

        assistant = parse_stream(stream).strip().strip('"').lower()

        if assistant.startswith('yes'):
            return True, summary
        elif assistant.startswith('no'):
            return False, summary
    
    print("WARNING - incorrect response in read_page_and_evaluate")
    return False, summary



def collate_answers(summaries, question):
    """
    Collates summaries of source information to create a report 
    answering the question. Includes references to sources in
    the text.
    """
    prompt = f"""You will be given a question and a collection of source-backed answers from a web search and your job is to collate the answers. You should only extract the information from the given text that is relevant to the question. This means that in your summary you're not supposed to include any information that isn't related to the question. Also don't include any information that isn't present in the provided answers - don't use your own knowledge under any circumstances. Another very important thing is the structure in which your text should be organized. You should notice all the points in all the answers and group those points into one summary of the point and then provide the links saying which answer includes the answer (every answer will have a website link associated with it - use that). If some answers contradict each other, that's very important and useful information - notice these situations and also write about it, giving links to sources. With all that, your text should be formatted with markdown with a `#` heading at the top being a fitting title, then a `##` heading for each point included in the answers (it's okay if there's only one and it's okay if there's many) where a summary of it should be. You can include `###` subheadings where it makes sense to expand on a point, for example to highlight any sources that contradict each other and the considerations coming from that. At the end of each `##` subheading you should list all the links to the answers that contain the information included in the section under the `##` subheading. Throughout the text of a single point (under a `##` subheading) you should include the links to the respective answer if that's possible - when a sentence is backed by a specific answer or answers. You will be given the question from the user next. Don't write anything more besides the collation. Try to include all the information included in the summaries but stay focused on answering the question. Don't add a list of sources at the end - that will be done automatically later."""

    answers = "\n".join([f'<answer source-link="{summary['url']}" ref={i}>\n{summary['summary']}\n</answer>' for i, summary in summaries.items()])

    messages = [
        {
            'role': 'system',
            'content': prompt
        },
        {
            'role': 'user',
            'content': question
        },
        {
            'role': 'system',
            'content': f"""Use the following list of source-backed answers to collate and answer the question from the user. If the answer isn't included in the text, then say you the source doesn't contain the information. Don't bring up any information you know, only summarize what's in the following texts to collate answers the question.\n\n<answers>\n{answers}\n</answers>\n\n\nTo reiterate the instructions:\n{prompt}"""
        }
    ]

    print(messages)

    stream = client.chat(
        model=COLLATE_MODEL, 
        messages=messages,
        stream=True
    )
    
    return parse_stream(stream)

def criticize_answer(question, answer):
    """
    Writes criticism of an answer report to later gain insight 
    into how to improve it.
    """

    prompt = f"""Here is a report based on a web search to answer the question "{question}".\n\n<report>{answer}\n</report>\n\nThis is just a first pass of building a holistic answer, thought process, and response. Consider how this report can be expanded, how it could be criticized, what is missing from it, and which sources are low quality."""

    messages = [
        {
            'role': 'user',
            'content': prompt
        }
    ]

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )

    assistant = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': assistant
    })

    return messages

def get_sources_to_remove(question, answer, chat_history):
    """
    Deprecated - not providing benefit.
    Based on criticism generated with criticize_answer(), determines 
    which sources are low quality and should be removed. Returns a list 
    of the reference numbers of the sources to remove.
    """

    prompt = """The report will need to be rewritten. What sources (if any) should definitely be removed from it before that's done? Say which should be definitely be removed and which maybe should be removed. Include the numbers of the sources as they are in the original report. The goal is to keep good quality, reputable sources. If all the sources are fine for an informed report, then you can say that none should be removed."""

    messages = chat_history[:]
    messages.append({
        'role': 'user',
        'content': prompt
    })

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )

    assistant = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': assistant
    })

    prompt = """Write down just the numbers of the sources that should **definitely** be removed as they are listed in the report. Don't include sources that "maybe" should be removed. Don't write anything else, just the numbers. Write them as a JSON list. Don't put it in a json codeblock, just write raw json."""

    messages.append({
        'role': 'user',
        'content': prompt
    })

    for retry in range(3):
        stream = client.chat(
            model=FAST_MODEL, 
            messages=messages,
            stream=True
        )

        assistant = parse_stream(stream).strip().replace('```json', '').replace('`', '')
        try:
            return list([int(i) for i in json.loads(assistant.strip())])
        except:
            print("retrying generating json")


def get_followup_questions(question, answer, chat_history):
    """
    Based on criticism generated with criticize_answer(), creates a list
    of follow-up questions to improve an answer report.
    """

    prompt = """The report will need to be rewritten. Based on your criticism, what further research should be done to expand this report? Formulate each new area to research as a question, then write a description why you think it's important."""

    messages = chat_history[:]
    messages.append({
        'role': 'user',
        'content': prompt
    })

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )

    assistant = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': assistant
    })

    prompt = """Which of these you think are the most important as a first step? Pick just a couple to start expanding the report."""

    messages.append({
        'role': 'user',
        'content': prompt
    })

    stream = client.chat(
        model=FAST_MODEL, 
        messages=messages,
        stream=True
    )

    assistant = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': assistant
    })

    prompt = """Write down just the questions for each of those in the format of a JSON list, where one question is one element. Don't write anything else besides that. Don't put it in a json codeblock, just write raw json."""

    messages.append({
        'role': 'user',
        'content': prompt
    })

    for retry in range(3):
        stream = client.chat(
            model=FAST_MODEL, 
            messages=messages,
            stream=True
        )

        assistant = parse_stream(stream).strip().replace('```json', '').replace('`', '')

        try:
            return json.loads(assistant.strip())
        except:
            print("retrying generating json")

def expand_answer(question, answer, followup_question, new_summaries):
    """
    Expands a previous answer report with a report written for a 
    follow-up question.
    """

    prompt = f"""You will be given a question and a collection of source-backed answers from a web search and your job is to collate the answers into a report. You should only extract the information from the given text that is relevant to the question. This means that in your report you're not supposed to include any information that isn't related to the question. Also don't include any information that isn't present in the provided answers - don't use your own knowledge under any circumstances. Another very important thing is the structure in which your text should be organized. You should notice all the points in all the answers and group those points into one summary of the point and then provide the links saying which answer includes the answer (every answer will have a website link associated with it - use that). If some answers contradict each other, that's very important and useful information - notice these situations and also write about it, giving links to sources. With all that, your report should be formatted with markdown with a `#` heading at the top being a fitting title, then a `##` heading for each point included in the answers (it's okay if there's only one and it's okay if there's many) where a summary of it should be. You can include `###` subheadings where it makes sense to expand on a point, for example to highlight any sources that contradict each other and the considerations coming from that. At the end of each `##` subheading you should list all the links to the answers that contain the information included in the section under the `##` subheading. Throughout the text of a single point (under a `##` subheading) you should include the links to the respective answer if that's possible - when a sentence is backed by a specific answer or answers. You will be given the question from the user next. Don't write anything more besides the collation. Try to include all the information included in the summaries but stay focused on answering the question. Don't add a list of sources at the end - that will be done automatically later."""

    answers = "\n".join([f'<answer source-link="{summary['url']}" ref={ref}>\n{summary['summary']}\n</answer>' for ref, summary in new_summaries.items()])


    messages = [
        {
            'role': 'system',
            'content': prompt
        },
        {
            'role': 'user',
            'content': question
        },
        {
            'role': 'system',
            'content': f"""Use the following list of source-backed answers to collate and answer the question from the user into a report. If the answer isn't included in the text, then say you the source doesn't contain the information. Don't bring up any information you know, only summarize what's in the following texts to collate answers the question.\n\n<answers>\n[ommited for brevity - answers already used]\n</answers>"""
        },
        {
            'role': 'assistant',
            'content': answer
        },
        {
            'role': 'user',
            'content': followup_question
        },
        {
            'role': 'system',
            'content': f"""Use the following list of source-backed answers to expand your previous report to the original question from the user. If the answer isn't included in the text, then say you the source doesn't contain the information. Don't bring up any information you know, only summarize what's in the following texts to collate answers the question. Don't write the Sources header and section - that will be added automatically later.\n\n<answers>\n{answers}\n</answers>\n\nExpand your original report using the sources provided.\n\n\nTo reiterate the instructions:\n{prompt}"""
        }
    ]

    print(messages)

    stream = client.chat(
        model=COLLATE_MODEL, 
        messages=messages,
        stream=True
    )
    
    new_answer = parse_stream(stream)

    messages.append({
        'role': 'assistant',
        'content': new_answer
    })

    messages.append({
        'role': 'user',
        'content': f'Now collate your report with the one you wrote earlier - join the report you just wrote with the following:\n\n{answer}\n\n\nJoin the two reports into one while keeping the same references and formatting.'
    })

    stream = client.chat(
        model=COLLATE_MODEL, 
        messages=messages,
        stream=True
    )
    
    final_answer = parse_stream(stream)

    return final_answer
