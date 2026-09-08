# ================================
# Standard library imports
# ================================
import json

# ================================
# Third-party imports
# ================================
from dotenv import load_dotenv
from openai import OpenAI
from IPython.display import display, HTML

# ================================
# Local / project imports
# ================================
import research_tools

# ================================
# Environment setup
# ================================
load_dotenv()  # Load environment variables from .env file

import unittests

# Instantiate OpenAI's client (you should use this in your graded functions)
CLIENT = OpenAI()

# * USING TOOLS: ARXIV + TAVILY
# arxiv_search_tool(query, max_results) – academic papers via arXiv API:
    # This tool searches arXiv and returns a list of papers with:
    # title, authors, published, summary, url, and (if available) link_pdf.

# Test the arXiv search tool
topic = "linear algebra"

arxiv_results = research_tools.arxiv_search_tool(topic, max_results=3)

# Show formatted arxiv_results
for i, paper in enumerate(arxiv_results, 1):
    if "error" in paper:
        print(f"❌ Error: {paper['error']}")
    else:
        print(f"📄 Paper {i}")
        print(f"  Title     : {paper['title']}")
        print(f"  Authors   : {', '.join(paper['authors'])}")
        print(f"  Published : {paper['published']}")
        print(f"  URL       : {paper['url']}\n")


print("\n🧾 Raw arxiv_Results:\n")
print(json.dumps(arxiv_results, indent=2))
{
# 📄 Paper 1
#   Title     : Linear Mappings of Free Algebra
#   Authors   : Aleks Kleyn
#   Published : 2010-03-08
#   URL       : http://arxiv.org/abs/1003.1544v2

# 🧾 Raw arxiv_Results:
# [
#   {
#     "title": "Linear Mappings of Free Algebra",
#     "authors": [
#       "Aleks Kleyn"
#     ],
#     "published": "2010-03-08",
#     "url": "http://arxiv.org/abs/1003.1544v2",
#     "summary": "For arbitrary F-algebra, in which the operation of addition is defined, I explore biring of matrices of mappings. 
#                 The sum of matrices is determined by the sum in F-algebra, and the product of matrices is determined by the product of mappings. 
#                 The system of equations, whose matrix is a matrix of mappings, is called a system of additive equations. 
#                 I considered the methods of solving system of additive equations. As an example, I consider the solution of a system of linear equations over the complex field provided 
#                 that the equations contain unknown quantities and their conjugates.\n  Linear mappings of algebra over a commutative ring preserve the operation of addition in algebra and the product of elements of the algebra by elements of the ring. 
#                 The representation of tensor product A\\otimes A in algebra A generates the set of linear transformations of algebra A.\n  The results of this research will be useful for mathematicians and physicists who deal with different algebras.",
#     "link_pdf": "https://arxiv.org/pdf/1003.1544v2"
#   },
}

# tavily_search_tool(query, max_results, include_images) – general web search via Tavily.
    # The tavily_search_tool calls the Tavily API to fetch web results. Returns a list of dicts:
    # title, content, url (and optional image URLs when include_images=True).

# Test the Tavily search tool
topic = "retrieval-augmented generation applications"

tavily_results = research_tools.tavily_search_tool(topic)
for item in tavily_results:
    print(item)
{
# {'title': 'Retrieval-augmented generation', 
# 'content': 'Finally, the LLM can generate output based on both the query and the retrieved documents. 
#             Some models incorporate extra steps to improve output, such as the re-ranking of retrieved information, context selection, 
#             and fine-tuning "Fine-tuning (deep learning)") ...,
# 'url: 'https://en.wikipedia.org/wiki/Retrieval-augmented_generation'}
}

# Tool mapping
TOOL_MAPPING = {
    "tavily_search_tool": research_tools.tavily_search_tool,
    "arxiv_search_tool": research_tools.arxiv_search_tool,
}

# * 1. Generate Research Report with Tools: generate_research_report_with_tools
def generate_research_report_with_tools(prompt: str, model: str = "gpt-4o") -> str:
    """
    Generates a research report using OpenAI's tool-calling with arXiv and Tavily tools.

    Args:
        prompt (str): The user prompt.
        model (str): OpenAI model name.

    Returns:
        str: Final assistant research report text.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant that can search the web and arXiv to write detailed, "
                "accurate, and properly sourced research reports.\n\n"
                "🔍 Use tools when appropriate (e.g., to find scientific papers or web content).\n"
                "📚 Cite sources whenever relevant. Do NOT omit citations for brevity.\n"
                "🌐 When possible, include full URLs (arXiv links, web sources, etc.).\n"
                "✍️ Use an academic tone, organize output into clearly labeled sections, and include "
                "inline citations or footnotes as needed.\n"
                "🚫 Do not include placeholder text such as '(citation needed)' or '(citations omitted)'."
            )
        },
        {"role": "user", "content": prompt}
    ]

    # List of available tools
    tools = [research_tools.arxiv_tool_def, research_tools.tavily_tool_def]

    # Maximum number of turns
    max_turns = 10
    
    # Iterate for max_turns iterations
    for _ in range(max_turns):

        ### START CODE HERE ###

        # Chat with the LLM via the client and set the correct arguments. Hint: Their names match names of variables already defined.
        # Make sure to let the LLM choose tools automatically. Hint: Look at the docs provided earlier!
        response = CLIENT.chat.completions.create( 
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=1, 
        ) 

        ### END CODE HERE ###

        # Get the response from the LLM and append to messages
        msg = response.choices[0].message 
        messages.append(msg) 

        # Stop when the assistant returns a final answer (no tool calls)
        if not msg.tool_calls:      
            final_text = msg.content
            print("✅ Final answer:")
            print(final_text)
            break

        # Execute tool calls and append results
        for call in msg.tool_calls:
            tool_name = call.function.name
            args = json.loads(call.function.arguments)
            print(f"🛠️ {tool_name}({args})")

            try:
                tool_func = TOOL_MAPPING[tool_name]
                result = tool_func(**args)
            except Exception as e:
                result = {"error": str(e)}

            ### START CODE HERE ###

            # Keep track of tool use in a new message
            new_msg = { 
                # Set role to "tool" (plain string) to signal a tool was used
                "role": "tool",
                # As stated in the markdown when inspecting the ChatCompletionMessage object 
                # every call has an attribute called id
                "tool_call_id": call.id,
                # The name of the tool was already defined above, use that variable
                "name": tool_name,
                # Pass the result of calling the tool to json.dumps
                "content": json.dumps(result)
            }

            ### END CODE HERE ###

            # Append to messages
            messages.append(new_msg)

    return final_text

# Test!
unittests.test_generate_research_report_with_tools(generate_research_report_with_tools)
{
# 🛠️ arxiv_search_tool({'query': 'radio observations of recurrent novae', 'max_results': 5})
# 🛠️ tavily_search_tool({'query': 'radio observations of recurrent novae', 'max_results': 5})
# ✅ Final answer:
# ## Radio Observations of Recurrent Novae

# Recurrent novae (RNe) are a fascinating subcategory of novae, characterized by multiple recorded outbursts, and they provide intriguing opportunities for study at various wavelengths, including radio. These systems involve a white dwarf and a companion star, typically in a symbiotic or cataclysmic variable configuration, where material from the companion accretes onto the white dwarf, leading to periodic thermonuclear explosions.

# ### Key Radio Observations

# 1. **RS Ophiuchi (RS Oph): A Notable Case**
#    - RS Oph is one of the most well-studied recurrent novae at radio wavelengths. It has been the subject of several radio observation campaigns following its outbursts. The first significant radio detection of its outburst was reported shortly after the optical maximum, just 18 days after the event, marking a substantial development as classical novae had previously been observed via radio only much later [Padin et al., 1985](https://www.nature.com/articles/315306a0).
#    - Subsequent very large baseline interferometry (VLBI) observations revealed a non-spherical ejection pattern and detailed the interactions between the ejected material and the pre-existing circumstellar environment [Taylor et al., 1989](https://adsabs.harvard.edu/pdf/1989MNRAS.237...81T).

# 2. **U Sco Observations**
#    - The recurrent nova U Scorpii has also undergone extensive observation. Archival Very Large Array (VLA) data covered the 1987 and 1999 eruptions, although these yielded nondetections in terms of radio emissions, showcasing the variability and difficulty in capturing radio phenomena depending on the timing and sensitivity of the observations [IOP Science](https://iopscience.iop.org/article/10.3847/1538-4365/ac24ab/pdf).

# 3. **Recent Developments and Understanding**
#    - Recent advancements in radio astronomy have afforded new insights into the physical processes occurring during nova outbursts. Radio studies are increasingly capable of measuring ejecta masses and monitoring the evolution of nova explosions over time, providing stringent tests against theoretical models [Selvelli, et al., 2008 & Patterson, et al., 1998](https://arxiv.org/html/1302.4455v1).

# ### The Role of Multiband Observations

# Recurrent novae such as T Pyxidis have been observed intensely across multiple wavelengths from radio to X-ray, broadening the understanding of these complex systems [AAVSO Review](https://www.aavso.org/recurrent-novae-review). Analyzing data across different electromagnetic bands helps elucidate the mass transfer rates, accretion processes, and the characteristics of explosions, which are crucial for refining models of nova behavior.

# ### Conclusion

# Radio observations of recurrent novae offer vital information on the dynamics of nova outbursts and the environments surrounding them. They highlight the importance of coordinated multi-wavelength observation strategies to capture the full scope of physical phenomena involved. The ongoing enhancement of radio astronomy technology promises to continue uncovering the secrets of these fascinating astronomical events.
#  All tests passed!
}

# * 2. Reflection + Rewrite: reflection_and_rewrite(report)
def reflection_and_rewrite(report, model: str = "gpt-4o-mini", temperature: float = 0.3) -> dict:
    """
    Generates a structured reflection AND a revised research report.
    Accepts raw text OR the messages list returned by generate_research_report_with_tools.

    Returns:
        dict with keys:
          - "reflection": structured reflection text
          - "revised_report": improved version of the input report
    """

    # Input can be plain text or a list of messages, this function detects and parses accordingly
    report = research_tools.parse_input(report)

    ### START CODE HERE ###

    # Define the prompt. A multi-line f-string is typically used for this.
    # Remember it should ask the model to output ONLY valid JSON with this structure:
    # {{ "reflection": "<text>", "revised_report": "<text>" }}
    user_prompt = f"""
    You are reviewing the following research report.

    Write a structured reflection covering these four aspects:
    1. Strengths — what the report does well.
    2. Limitations — gaps, weak evidence, missing citations, or unclear reasoning.
    3. Suggestions — concrete ways to improve clarity, structure, or rigor.
    4. Opportunities — additional angles, sources, or analysis that could strengthen the report.

    Then, using that reflection, rewrite the report as a revised version that fixes the
    identified issues, improves clarity and academic tone, and preserves all citations and URLs.

    Return ONLY valid JSON, with no markdown formatting, no code fences, and no extra text,
    in exactly this structure:
    {{
        "reflection": "<your structured reflection text here>",
        "revised_report": "<the improved report text here>"
    }}

    Here is the report to review:
    \"\"\"
    {report}
    \"\"\"
    """

    # Get a response from the LLM
    response = CLIENT.chat.completions.create( 
        # Pass in the model
        model=model,
        messages=[ 
            # System prompt is already defined
            {"role": "system", "content": "You are an academic reviewer and editor."},
            # Add user prompt
            {"role": "user", "content": user_prompt},
        ],
        # Set the temperature equal to the temperature parameter passed to the function
        temperature=temperature
    )

    ### END CODE HERE ###

    # Extract output
    llm_output = response.choices[0].message.content.strip()

    # Check if output is valid JSON
    try:
        data = json.loads(llm_output)
    except json.JSONDecodeError:
        raise Exception("The output of the LLM was not valid JSON. Adjust your prompt.")

    return {
        "reflection": str(data.get("reflection", "")).strip(),
        "revised_report": str(data.get("revised_report", "")).strip(),
    }

# * 3. Convert Report to HTML
def convert_report_to_html(report, model: str = "gpt-4o", temperature: float = 0.5) -> str:
    """
    Converts a plaintext research report into a styled HTML page using OpenAI.
    Accepts raw text OR the messages list from the tool-calling step.
    """

    # Input can be plain text or a list of messages, this function detects and parses accordingly
    report = research_tools.parse_input(report)

    # System prompt is already provided
    system_prompt = "You convert plaintext reports into full clean HTML documents."

    ### START CODE HERE ###
    
    # Build the user prompt instructing the model to return ONLY valid HTML
    user_prompt = f"""
    Convert the following research report into a complete, well-structured HTML document.

    Requirements:
    - Include proper <!DOCTYPE html>, <html>, <head>, and <body> tags.
    - Add a <title> based on the report's content.
    - Include a <style> block in the <head> with clean, readable CSS
    (readable font, comfortable line-height, reasonable max-width, margins).
    - Use semantic HTML: <h1> for the title, <h2>/<h3> for sections, <p> for paragraphs,
    <ul>/<ol> for lists, and <a href="..."> for any URLs or citations found in the text.
    - Preserve all citations, references, and URLs exactly as given — do not omit or alter them.
    - Return ONLY the raw HTML document, with no markdown code fences (no ```html),
    no explanations, and no extra text before or after the HTML.

    Here is the report to convert:
    \"\"\"
    {report}
    \"\"\"
    """

    # Call the LLM by interacting with the CLIENT. 
    # Remember to set the correct values for the model, messages (system and user prompts) and temperature
    response = CLIENT.chat.completions.create( 
        model=model,
        messages=[ 
            {"role": "system", "content": "You are an academic reviewer and editor."},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature
    )

    ### END CODE HERE ###

    # Extract the HTML from the assistant message
    html = response.choices[0].message.content.strip()  

    return html

# * End-to-End Pipeline
# 1. Generate a research report (tools).
# 2. Reflect on the report.
# 3. Convert the report to HTML.

# 1) Research with tools
prompt_ = "Radio observations of recurrent novae"
preliminary_report = generate_research_report_with_tools(prompt_)
print("=== Research Report (preliminary) ===\n")
print(preliminary_report)

# 2) Reflection on the report (use the final TEXT to avoid ambiguity)
reflection_text = reflection_and_rewrite(preliminary_report)   # <-- pass text, not messages
print("=== Reflection on Report ===\n")
print(reflection_text['reflection'], "\n")
print("=== Revised Report ===\n")
print(reflection_text['revised_report'], "\n")


# 3) Convert the report to HTML (use the TEXT and correct function name)
html = convert_report_to_html(reflection_text['revised_report'])

print("=== Generated HTML (preview) ===\n")
print((html or "")[:600], "\n... [truncated]\n")

# 4) Display full HTML
display(HTML(html))
{
# 🛠️ arxiv_search_tool({'query': 'radio observations of recurrent novae', 'max_results': 5})
# ✅ Final answer:
# ## Radio Observations of Recurrent Novae

# ### 1. Overview
# Recurrent novae are a type of cataclysmic variable star system that experience repeated nova outbursts due to thermonuclear runaways on the surface of a white dwarf accreting material from a companion star. Radio observations provide insights into the ejecta behavior and characteristics of these phenomena, revealing critical information about their evolution.

# ### 2. Key Studies and Findings

# - **Lesson learned from some recurrent novae**  
#   Elena Mason and Frederick M. Walters in their 2013 study discuss early decline and nebular spectra of recurrent novae such as YY Dor and nova LMC 2009. These novae share similar spectral features and evolutionary characteristics, suggesting commonalities in their white dwarf progenitors and their post-outburst phases[1](http://arxiv.org/abs/1303.2776v1).

# - **Shocks and Ejecta Mass: Radio Observations of Nova V1723 Aql**  
#   Jennifer H. S. Weston et al. conducted a comprehensive study on classical nova V1723 Aql, which is relevant to understanding recurrent novae due to shared characteristics. Their observations via the Karl G. Jansky Very Large Array (VLA) suggested that ejecta mass estimates from radio models often exceed theoretical expectations. The discovery of an initial bump in the radio light curve indicated the presence of shock materials in the ejected shell, which provide insights into mass loss history and density profiles[2](http://arxiv.org/abs/1306.2265v2).

# ### 3. Relevance of Radio Observations
# Radio observations are particularly significant in the study of novae because they enable astronomers to probe the density, mass, and distribution of ejecta without interference from the optical brightness of the nova. These observations also provide temporal evolution data, revealing the dynamics of the outflow and interactions with the surrounding medium.

# ### 4. Challenges and Future Directions
# Radio observations of novae are challenged by radio frequency interference and the need for precise instruments capable of detecting faint signals from distant celestial events. Further technological advancements and increased sensitivity in radio telescopes are expected to enhance the detail and accuracy of observations, providing deeper insights into both classical and recurrent novae.

# For ongoing research, enhancements in computational models for interpreting radio data could refine our understanding of nova explosions and the role of shocks and ejecta mass in these powerful cosmic phenomena.

# ---

# For further reading, interested researchers can refer to the full-text articles available via the provided links to arXiv: [1](https://arxiv.org/pdf/1303.2776v1), [2](https://arxiv.org/pdf/1306.2265v2).
# === Research Report (preliminary) ===

# ## Radio Observations of Recurrent Novae

# ### 1. Overview
# Recurrent novae are a type of cataclysmic variable star system that experience repeated nova outbursts due to thermonuclear runaways on the surface of a white dwarf accreting material from a companion star. Radio observations provide insights into the ejecta behavior and characteristics of these phenomena, revealing critical information about their evolution.

# ### 2. Key Studies and Findings

# - **Lesson learned from some recurrent novae**  
#   Elena Mason and Frederick M. Walters in their 2013 study discuss early decline and nebular spectra of recurrent novae such as YY Dor and nova LMC 2009. These novae share similar spectral features and evolutionary characteristics, suggesting commonalities in their white dwarf progenitors and their post-outburst phases[1](http://arxiv.org/abs/1303.2776v1).

# - **Shocks and Ejecta Mass: Radio Observations of Nova V1723 Aql**  
#   Jennifer H. S. Weston et al. conducted a comprehensive study on classical nova V1723 Aql, which is relevant to understanding recurrent novae due to shared characteristics. Their observations via the Karl G. Jansky Very Large Array (VLA) suggested that ejecta mass estimates from radio models often exceed theoretical expectations. The discovery of an initial bump in the radio light curve indicated the presence of shock materials in the ejected shell, which provide insights into mass loss history and density profiles[2](http://arxiv.org/abs/1306.2265v2).

# ### 3. Relevance of Radio Observations
# Radio observations are particularly significant in the study of novae because they enable astronomers to probe the density, mass, and distribution of ejecta without interference from the optical brightness of the nova. These observations also provide temporal evolution data, revealing the dynamics of the outflow and interactions with the surrounding medium.

# ### 4. Challenges and Future Directions
# Radio observations of novae are challenged by radio frequency interference and the need for precise instruments capable of detecting faint signals from distant celestial events. Further technological advancements and increased sensitivity in radio telescopes are expected to enhance the detail and accuracy of observations, providing deeper insights into both classical and recurrent novae.

# For ongoing research, enhancements in computational models for interpreting radio data could refine our understanding of nova explosions and the role of shocks and ejecta mass in these powerful cosmic phenomena.

# ---

# For further reading, interested researchers can refer to the full-text articles available via the provided links to arXiv: [1](https://arxiv.org/pdf/1303.2776v1), [2](https://arxiv.org/pdf/1306.2265v2).
# === Reflection on Report ===

# 1. Strengths: The report provides a clear overview of recurrent novae and emphasizes the importance of radio observations in understanding these phenomena. It effectively summarizes key studies and findings, highlighting significant contributions from notable researchers. The relevance of radio observations is well-articulated, and the challenges faced in this field are acknowledged, which adds depth to the discussion. 2. Limitations: The report lacks a comprehensive literature review, missing citations for some claims, particularly regarding the significance of radio observations and their implications. There is also a lack of detailed explanation about the mechanisms of thermonuclear runaways and how they relate to the observed phenomena. Additionally, the report could benefit from a clearer structure, particularly in differentiating between the studies discussed. 3. Suggestions: To improve clarity, the report should include a brief explanation of thermonuclear runaways and their relevance to recurrent novae. Each study could be presented in a more structured format, perhaps with subheadings for clarity. Including more recent studies and a broader range of sources would enhance the rigor of the report. 4. Opportunities: The report could explore additional angles, such as the implications of radio observations for understanding the evolutionary pathways of white dwarfs. Including more recent advancements in radio astronomy techniques and their applications to novae research would strengthen the report. Additionally, discussing the potential for multi-wavelength studies could provide a more holistic view of nova phenomena. 

# === Revised Report ===

# ## Radio Observations of Recurrent Novae

# ### 1. Overview
# Recurrent novae are a type of cataclysmic variable star system that experience repeated nova outbursts due to thermonuclear runaways on the surface of a white dwarf accreting material from a companion star. Understanding the mechanisms behind these thermonuclear runaways is crucial for comprehending the evolution of these systems. Radio observations provide insights into the ejecta behavior and characteristics of these phenomena, revealing critical information about their evolution and the dynamics of their outflows.

# ### 2. Key Studies and Findings

# - **Lessons Learned from Recurrent Novae**  
#   In their 2013 study, Elena Mason and Frederick M. Walters discuss the early decline and nebular spectra of recurrent novae such as YY Dor and nova LMC 2009. These novae share similar spectral features and evolutionary characteristics, suggesting commonalities in their white dwarf progenitors and their post-outburst phases [1](http://arxiv.org/abs/1303.2776v1).

# - **Shocks and Ejecta Mass: Radio Observations of Nova V1723 Aql**  
#   Jennifer H. S. Weston et al. conducted a comprehensive study on classical nova V1723 Aql, which is relevant to understanding recurrent novae due to shared characteristics. Their observations via the Karl G. Jansky Very Large Array (VLA) suggested that ejecta mass estimates from radio models often exceed theoretical expectations. The discovery of an initial bump in the radio light curve indicated the presence of shock materials in the ejected shell, providing insights into mass loss history and density profiles [2](http://arxiv.org/abs/1306.2265v2).

# ### 3. Relevance of Radio Observations
# Radio observations are particularly significant in the study of novae because they enable astronomers to probe the density, mass, and distribution of ejecta without interference from the optical brightness of the nova. These observations also provide temporal evolution data, revealing the dynamics of the outflow and interactions with the surrounding medium. The ability to observe these phenomena across different wavelengths enhances our understanding of their complexities.

# ### 4. Challenges and Future Directions
# Radio observations of novae face challenges such as radio frequency interference and the need for precise instruments capable of detecting faint signals from distant celestial events. Further technological advancements and increased sensitivity in radio telescopes are expected to enhance the detail and accuracy of observations, providing deeper insights into both classical and recurrent novae. 

# For ongoing research, enhancements in computational models for interpreting radio data could refine our understanding of nova explosions and the role of shocks and ejecta mass in these powerful cosmic phenomena. Additionally, exploring multi-wavelength studies could provide a more comprehensive view of the dynamics involved in nova events.

# ---

# For further reading, interested researchers can refer to the full-text articles available via the provided links to arXiv: [1](https://arxiv.org/pdf/1303.2776v1), [2](https://arxiv.org/pdf/1306.2265v2). 

# === Generated HTML (preview) ===

# ```html
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Radio Observations of Recurrent Novae</title>
#     <style>
#         body {
#             font-family: Arial, sans-serif;
#             line-height: 1.6;
#             max-width: 800px;
#             margin: 20px auto;
#             padding: 0 10px;
#         }
#         h1, h2, h3 {
#             color: #333;
#         }
#         a {
#             color: #0066cc;
#             text-decoration: none;
#         }
#         a:hover {
#             text-decoration: unde 
# ... [truncated]

# ```html
# Radio Observations of Recurrent Novae
# 1. Overview
# Recurrent novae are a type of cataclysmic variable star system that experience repeated nova outbursts due to thermonuclear runaways on the surface of a white dwarf accreting material from a companion star. Understanding the mechanisms behind these thermonuclear runaways is crucial for comprehending the evolution of these systems. Radio observations provide insights into the ejecta behavior and characteristics of these phenomena, revealing critical information about their evolution and the dynamics of their outflows.

# 2. Key Studies and Findings
# Lessons Learned from Recurrent Novae
# In their 2013 study, Elena Mason and Frederick M. Walters discuss the early decline and nebular spectra of recurrent novae such as YY Dor and nova LMC 2009. These novae share similar spectral features and evolutionary characteristics, suggesting commonalities in their white dwarf progenitors and their post-outburst phases [1].
# Shocks and Ejecta Mass: Radio Observations of Nova V1723 Aql
# Jennifer H. S. Weston et al. conducted a comprehensive study on classical nova V1723 Aql, which is relevant to understanding recurrent novae due to shared characteristics. Their observations via the Karl G. Jansky Very Large Array (VLA) suggested that ejecta mass estimates from radio models often exceed theoretical expectations. The discovery of an initial bump in the radio light curve indicated the presence of shock materials in the ejected shell, providing insights into mass loss history and density profiles [2].
# 3. Relevance of Radio Observations
# Radio observations are particularly significant in the study of novae because they enable astronomers to probe the density, mass, and distribution of ejecta without interference from the optical brightness of the nova. These observations also provide temporal evolution data, revealing the dynamics of the outflow and interactions with the surrounding medium. The ability to observe these phenomena across different wavelengths enhances our understanding of their complexities.

# 4. Challenges and Future Directions
# Radio observations of novae face challenges such as radio frequency interference and the need for precise instruments capable of detecting faint signals from distant celestial events. Further technological advancements and increased sensitivity in radio telescopes are expected to enhance the detail and accuracy of observations, providing deeper insights into both classical and recurrent novae.

# For ongoing research, enhancements in computational models for interpreting radio data could refine our understanding of nova explosions and the role of shocks and ejecta mass in these powerful cosmic phenomena. Additionally, exploring multi-wavelength studies could provide a more comprehensive view of the dynamics involved in nova events.

# For further reading, interested researchers can refer to the full-text articles available via the provided links to arXiv: [1], [2].

# ```
}