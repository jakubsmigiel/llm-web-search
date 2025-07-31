import question_agent

"""
1. Answer the question by finding sources to answer the question and write the report
2. Write criticism of the report
3. Based on the criticism, create follow-up questions to the report.
4. For each of the followup questions, find sources and use them to expand the report.
"""

question = input("question: ")
should_write_extended = 'x'
while should_write_extended not in 'yn':
    should_write_extended = input("extend the report when it's done? [y/n] ").lower().strip()

answer, sources = question_agent.answer_question(question)
print("Simple report:")
print(answer)
print("\n")

if should_write_extended == 'y':
    followup_questions = question_agent.get_followup_questions(question, answer, sources)
    print("Follow-up questions:")
    print("\n- ".join(followup_questions))

    expanded_answer, new_sources = question_agent.expand_answer_with_followup_questions(question, answer, followup_questions, sources)
    print("\n\n\n\nExtended report:\n")
    print(expanded_answer)