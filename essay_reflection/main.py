from dotenv import load_dotenv
import aisuite as ai
from utils import show_output

CLIENT = ai.Client()
load_dotenv()

# * OBJECTIVE 1: Write a function called generate_draft that takes in a string topic and uses a language model to generate a complete draft essay.
# OUTPUT: A string representing the full draft of the essay
def generate_draft(topic: str, model: str = "openai:gpt-4o") -> str: 
    
    ### START CODE HERE ###

    # Define your prompt here. A multi-line f-string is typically used for this.
    prompt = f"""
    Write a complete draft essay on the following topic: {topic}
    
    Requirements:
    - Include a clear introduction that presents the main argument or thesis.
    - Develop 2-4 body paragraphs, each covering a distinct point that supports the thesis.
    - Include a conclusion that summarizes the key points and reinforces the thesis.
    - Write in a clear, coherent, and well-organized styyle.
    - Aim for approximately 400-600 words.
    """

    ### END CODE HERE ###
    
    # Get a response from the LLM by creating a chat with the client.
    response = CLIENT.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )

    return response.choices[0].message.content


# * OBJECTIVE 2: Write a function called reflect_on_draft that takes a previously generated essay draft and uses a language model to provide constructive feedback.
# OUTPUT: A string with feedback in paragraph form.
# REQUIREMENTS:
    # The feedback should be critical but constructive.
    # It should address issues such as structure, clarity, strength of argument, and writing style.
    # The function should send the draft to the model and return its response.
def reflect_on_draft(draft: str, model: str = "openai:o4-mini") -> str:

    ### START CODE HERE ###

    # Define your prompt here. A multi-line f-string is typically used for this.
    prompt = f"""
    You are an experienced essay editor. Carefully review the following essay draft and provide constructive, actionable feedback to help improve it.
    
    Essay draft:
    \"\"\"
    {draft}
    \"\"\"
    
    In your feedback, address:
    - Clarity and strength of the thesis/main argument.
    - Whether each body paragraph is well-supported and logically connected to the thesis.
    - Structure, flow, and transistions between paragraphs.
    - Areas that are weak, repetitive, vague, or could be cut.
    - Specific suggestions for improvement (not just general praise).
    
    Be honest and specific. Do not rewrite the essay - only provide feedback on it.
    """

    ### END CODE HERE ###

    # Get a response from the LLM by creating a chat with the client.
    response = CLIENT.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )

    return response.choices[0].message.content


# * OBJECTIVE 3: Implement a function called revise_draft that improves a given essay draft based on feedback from a reflection step.
# OUTPUT: A string containing the revised and improved essay.
# Requirements:
    # The revised draft should address the issues mentioned in the feedback.
    # It should improve clarity, coherence, argument strength, and overall flow.
    # The function should use the feedback to guide the revision, and return only the final revised essay.
def revise_draft(original_draft: str, reflection: str, model: str = "openai:gpt-4o") -> str:

    ### START CODE HERE ###

    # Define your prompt here. A multi-line f-string is typically used for this.
    prompt = f"""
    You are an experienced essay writer. Revise the essay draft below based on the feedback provided, producing an improved, complete version of the essay.

    Original draft:
    \"\"\"
    {original_draft}
    \"\"\"

    Feedback to address:
    \"\"\"
    {reflection}
    \"\"\"

    Instructions:
    - Carefully incorporate the feedback to improve clarity, structure, and argument strength.
    - Preserve the original topic and core ideas, but rewrite or restructure passages as needed to address the feedback.
    - Ensure the essay still has a clear introduction, well-supported body paragraphs, and a conclusion.
    - The revised essay must be a complete, full-length essay of at least 400 words (well over 100 characters).
    - Return only the final revised essay text, with no additional commentary, headers, or explanation of the changes made.
    """

    # Get a response from the LLM by creating a chat with the client.
    response = CLIENT.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )

    ### END CODE HERE ###

    return response.choices[0].message.content


# * TESTING
essay_prompt = "Should social media platforms be regulated by the government?"

# Agent 1 – Draft
draft = generate_draft(essay_prompt)
print("📝 Draft:\n")
print(draft)

# Agent 2 – Reflection
feedback = reflect_on_draft(draft)
print("\n🧠 Feedback:\n")
print(feedback)

# Agent 3 – Revision
revised = revise_draft(draft, feedback)
print("\n✍️ Revised:\n")
print(revised)


essay_prompt = "Should social media platforms be regulated by the government?"

show_output("Step 1 – Draft", draft, background="#fff8dc", text_color="#333333")
show_output("Step 2 – Reflection", feedback, background="#e0f7fa", text_color="#222222")
show_output("Step 3 – Revision", revised, background="#f3e5f5", text_color="#222222")