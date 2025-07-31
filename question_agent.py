"""
Strings together functions from search, llm, and browser to 
create the AI agent
"""

import search
import llm
import browser
import cache

MAX_SOURCES = 6

def get_sources(question, starting_ref=1):
    """
    Searches the web for sources, evaluates each search result for
    relevance to ignore irrelevant ones, and summarizes the contents of 
    each result.
    """

    query = cache.uncache(f'{question}-{starting_ref}-query')
    if query is None: 
        query = llm.generate_search_query(question)
        cache.cache(f'{question}-{starting_ref}-query', query)

    sources = cache.uncache(f'{question}-{starting_ref}-sources')
    if sources is None:
        search_results = search.google_search(query)
        sources = {}
        for i, search_result in enumerate(search_results):
            link = search_result['href']
            text = browser.scrape_trafilatura(link)
            if text is None:
                print('skipping ', link)
                continue
            print('adding   ', link)
            print('reading  ', link)
            is_valid_source, summary = llm.read_page_and_evaluate(text, question)
            if not is_valid_source:
                print('source irrelevant or invalid')
                continue
            sources[str(int(i)+starting_ref)] = {
                'title': search_result['title'],
                'url': link,
                'content': text,
                'summary': summary
            }
            if len(sources) >= MAX_SOURCES:
                break

        print(f"\nscraped {len(sources)} sources.\n")
    
        cache.cache(f'{question}-{starting_ref}-sources', sources)

    return sources

def answer_question(question, sources=None, starting_ref=1):
    answer = cache.uncache(f'{question+str(sources)}-answer')
    if answer is not None:
        sources = cache.uncache(f'{question}-{starting_ref}-sources')
        return answer, sources
    
    sources_were_none = sources is None
    if sources is None:
        sources = get_sources(question, starting_ref=starting_ref)

    answer = ""
    print("\ncollating summaries")
    collated = llm.collate_answers(sources, question)

    answer += collated

    answer += "\n\n# Sources\n"
    for ref, source in sources.items():
        answer += f'- [{ref}] [{source["title"]}]({source['url']})\n'
        
    cache.cache(f'{question+str(sources)}-answer', answer)
    if sources_were_none: cache.cache(f'{question+str(None)}-answer', answer)
    return answer, sources

def expand_answer(question, answer, followup_question, starting_ref):
    """
    Expands an answer report with another report.
    """
    new_sources = get_sources(followup_question, starting_ref=starting_ref)

    expanded_answer = cache.uncache(f'{question}-{followup_question}-expanded_answer')
    if expanded_answer is None:
        expanded_answer = llm.expand_answer(question, answer, followup_question, new_sources)
        cache.cache(f'{question}-{followup_question}-expanded_answer', expanded_answer)
    
    return expanded_answer, new_sources

def get_followup_questions(question, answer, sources):
    """
    Writes criticism of the original answer report and produces follow-up
    questions to expand the report with.
    """

    criticism = cache.uncache(f'{question}-{str(sources)}-criticism')
    if criticism is None:
        criticism = llm.criticize_answer(question, answer)
        cache.cache(f'{question}-{str(sources)}-criticism', criticism)
    
    # Deprecated removing low quality sources
    # sources_to_remove = cache.uncache(f'{question}-{str(sources)}-sources_to_remove')
    # if sources_to_remove is None:
    #     sources_to_remove = llm.get_sources_to_remove(question, answer, criticism)
    #     cache.cache(f'{question}-{str(sources)}-sources_to_remove', sources_to_remove)
    # good_sources = {ref: source for ref, source in sources.items() if int(ref) not in sources_to_remove}
    # rewritten = cache.uncache(f'{question}-{str(sources)}-rewritten')
    # if rewritten is None:
    #     rewritten = answer_question(question, sources=good_sources)
    #     cache.cache(f'{question}-{str(sources)}-rewritten', rewritten)

    followup_questions = cache.uncache(f'{question}-{str(sources)}-followup_questions')
    if followup_questions is None:
        followup_questions = llm.get_followup_questions(question, answer, criticism)
        cache.cache(f'{question}-{str(sources)}-followup_questions', followup_questions)
    
    return followup_questions

def expand_answer_with_followup_questions(question, answer, followup_questions, sources):
    """
    Expands an answer report by writing another report on 
    a follow-up question and combining the reports.
    """
    new_sources = sources
    expanded_answer = answer
    for followup_question in followup_questions:
        expanded_answer, sources = expand_answer(question, expanded_answer, followup_question, max([int(k) for k in new_sources.keys()])+1)
        new_sources.update(sources)
    
    expanded_answer += "\n\n# Sources\n"
    for ref, source in new_sources.items():
        expanded_answer += f'- [{ref}] [{source["title"]}]({source['url']})\n'

    return expanded_answer, new_sources


if __name__ == '__main__':
    question = input("question: ")
    print(answer_question(question)[0])
