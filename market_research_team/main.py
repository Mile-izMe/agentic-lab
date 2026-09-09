# =========================
# Imports
# =========================

# --- Standard library ---
import base64
import json
import os
import re
from datetime import datetime
from io import BytesIO

# --- Third-party ---
import requests
import openai
from PIL import Image
from dotenv import load_dotenv
from IPython.display import Markdown, display
import aisuite
import base64

# --- Local / project ---
import tools
import utils


# =========================
# Environment & Client
# =========================
load_dotenv()
client = aisuite.Client()

tools.tavily_search_tool('trends in sunglasses fashion')
tools.product_catalog_tool()

# * BUILDING TEAMS
# NOTE: Market Research Agent
def market_research_agent(return_messages: bool = False):

    utils.log_agent_title_html("Market Research Agent", "🕵️‍♂️")

    prompt_ = f"""
    You are a fashion market research agent tasked with preparing a trend analysis for a summer sunglasses campaign.

    Your goal:
    1. Explore current fashion trends related to sunglasses using web search.
    2. Review the internal product catalog to identify items that align with those trends.
    3. Recommend one or more products from the catalog that best match emerging trends.
    4. If needed, today date is {datetime.now().strftime("%Y-%m-%d")}.

    You can call the following tools:
    - tavily_search_tool: to discover external web trends.
    - product_catalog_tool: to inspect the internal sunglasses catalog.

    Once your analysis is complete, summarize:
    - The top 2–3 trends you found.
    - The product(s) from the catalog that fit these trends.
    - A justification of why they are a good fit for the summer campaign.
    """
    messages = [{"role": "user", "content": prompt_}]
    tools_ = tools.get_available_tools()

    while True:
        response = client.chat.completions.create(
            model="openai:o4-mini",
            messages=messages,
            tools=tools_,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        if msg.content:
            utils.log_final_summary_html(msg.content)
            return (msg.content, messages) if return_messages else msg.content

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                utils.log_tool_call_html(tool_call.function.name, tool_call.function.arguments)
                result = tools.handle_tool_call(tool_call)
                utils.log_tool_result_html(result)

                messages.append(msg)
                messages.append(tools.create_tool_response_message(tool_call, result))
        else:
            utils.log_unexpected_html()
            return ("[⚠️ Unexpected: No tool_calls or content returned]", messages) if return_messages else "[⚠️ Unexpected: No tool_calls or content returned]"


# NOTE: Graphic Design Agent
def graphic_designer_agent(trend_insights: str, caption_style: str = "short punchy", size: str = "1024x1024") -> dict:
    utils.log_agent_title_html("Graphic Designer Agent", "🎨")

    # Step 1: Generate prompt and caption using aisuite
    system_message = (
        "You are a visual marketing assistant. Based on the input trend insights, "
        "write a creative and visual prompt for an AI image generation model, and also a short caption."
    )
    user_prompt = f"""
    Trend insights:
    {trend_insights}
    Please output:
    1. A vivid, descriptive prompt to guide image generation.
    2. A marketing caption in style: {caption_style}.
    Respond in this format:
    {{"prompt": "...", "caption": "..."}}
    """
    chat_response = client.chat.completions.create(
        model="openai:o4-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ]
    )
    content = chat_response.choices[0].message.content.strip()
    match = re.search(r'\{.*\}', content, re.DOTALL)
    parsed = json.loads(match.group(0)) if match else {"error": "No JSON returned", "raw": content}
    prompt = parsed["prompt"]
    caption = parsed["caption"]

    # Step 2: Generate image with gpt-image-1-mini (returns base64, not URL)
    openai_client = openai.OpenAI()
    image_response = openai_client.images.generate(
        model="gpt-image-1-mini",
        prompt=prompt,
        size=size,
        quality="medium",   # gpt-image-1 accepts: low | medium | high | auto
        n=1,
        # no response_format — gpt-image-1 always returns b64_json
    )

    b64 = image_response.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    img = Image.open(BytesIO(img_bytes))

    image_path = "generated_image.png"
    img.save(image_path)

    utils.log_final_summary_html(f"""
        <h3>Generated Image and Caption</h3>
        <p><strong>Image Path:</strong> <code>{image_path}</code></p>
        <p><strong>Generated Image:</strong></p>
        <img src="{image_path}" alt="Generated Image" style="max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 8px; margin-top: 10px; margin-bottom: 10px;">
        <p><strong>Prompt:</strong> {prompt}</p>
    """)

    return {
        "image_path": image_path,
        "prompt": prompt,
        "caption": caption,
    }

# NOTE: Copy Writer Agent
def copywriter_agent(image_path: str, trend_summary: str, model: str = "openai:o4-mini") -> dict:

    """
    Uses aisuite (OpenAI only) to send an image and a trend summary and return a campaign quote.

    Args:
        image_path (str): URL of the image to be analyzed.
        trend_summary (str): Text from the researcher agent.
        model (str): OpenAI model (e.g., openai:o4-mini, openai:gpt-4o)

    Returns:
        dict: {
            "quote": "...",
            "justification": "...",
            "image_path": "..."
        }
    """

    utils.log_agent_title_html("Copywriter Agent", "✍️")

    # Step 1: Load local image and encode as base64
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    # Step 2: Build OpenAI-compliant multimodal message
    messages = [
        {
            "role": "system",
            "content": "You are a copywriter that creates elegant campaign quotes based on an image and a marketing trend summary."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_img}",
                        "detail": "auto"
                    }
                },
                {
                    "type": "text",
                    "text": f"""
                    Here is a visual marketing image and a trend analysis:

                    Trend summary:
                    \"\"\"{trend_summary}\"\"\"

                    Please return a JSON object like:
                    {{
                    "quote": "A short, elegant campaign phrase (max 12 words)",
                    "justification": "Why this quote matches the image and trend"
                    }}"""
                }
            ]
        }
    ]

    # Step 3: Send request via aisuite
    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    # Step 4: Parse JSON response
    content = response.choices[0].message.content.strip()

    utils.log_final_summary_html(content)

    try:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        parsed = json.loads(match.group(0)) if match else {"error": "No valid JSON returned"}
    except Exception as e:
        parsed = {"error": f"Failed to parse: {e}", "raw": content}


    parsed["image_path"] = image_path
    return parsed

# NOTE: Packaging Agent
def packaging_agent(trend_summary: str, image_url: str, quote: str, justification: str, output_path: str = "campaign_summary.md") -> str:

    """
    Packages the campaign assets into a beautifully formatted markdown report for executive review.

    Args:
        trend_summary (str): Summary of the market trends.
        image_url (str): URL of the campaign image.
        quote (str): Marketing quote to overlay.
        justification (str): Explanation for the quote.
        output_path (str): Path to save the markdown report.

    Returns:
        str: Path to the saved markdown file.
    """

    utils.log_agent_title_html("Packaging Agent", "📦")

    # We use this path in the src of the <img>
    styled_image_html = f"""
    ![Open the generated file to see]({image_url})
        """

    beautified_summary = client.chat.completions.create(
            model="openai:o4-mini",
            messages=[
                {"role": "system", "content": "You are a marketing communication expert writing elegant campaign summaries for executives."},
                {"role": "user", "content": f"""
            Please rewrite the following trend summary to be clear, professional, and engaging for a CEO audience:

            \"\"\"
            {trend_summary.strip()}
            \"\"\"
            """}
        ]
    ).choices[0].message.content.strip()

    utils.log_tool_result_html(beautified_summary)

    # Combine all parts into markdown
    markdown_content = f"""# 🕶️ Summer Sunglasses Campaign – Executive Summary

## 📊 Refined Trend Insights
{beautified_summary}

## 🎯 Campaign Visual
{styled_image_html}

## ✍️ Campaign Quote
{quote.strip()}

## ✅ Why This Works
{justification.strip()}

---

*Report generated on {datetime.now().strftime('%Y-%m-%d')}*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return output_path

# NOTE: PIPELINE END_TO_END
def run_sunglasses_campaign_pipeline(output_path: str = "campaign_summary.md") -> dict:
    """
    Runs the full summer sunglasses campaign pipeline:
    1. Market research (search trends + match products)
    2. Generate visual + caption
    3. Generate quote based on image + trend
    4. Create executive markdown report

    Returns:
    dict: Dictionary containing all intermediate results + path to final report
    """
    # 1. Run market research agent
    trend_summary = market_research_agent()
    print("✅ Market research completed")

    # 2. Generate image + caption
    visual_result = graphic_designer_agent(trend_insights=trend_summary)
    image_path = visual_result["image_path"]
    print("🖼️ Image generated")

    # 3. Generate quote based on image + trends
    quote_result = copywriter_agent(image_path=image_path, trend_summary=trend_summary)
    quote = quote_result.get("quote", "")
    justification = quote_result.get("justification", "")
    print("💬 Quote created")

    # 4. Generate markdown report
    md_path = packaging_agent(
        trend_summary=trend_summary,
        image_url=image_path,  
        quote=quote,
        justification=justification,
        output_path=f"campaign_summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
    )

    print(f"📦 Report generated: {md_path}")

    return {
        "trend_summary": trend_summary,
        "visual": visual_result,
        "quote": quote_result,
        "markdown_path": md_path
    }

results = run_sunglasses_campaign_pipeline()
{
# 🕵️‍♂️ Market Research Agent
# 📞 Tool Call: tavily_search_tool
# {"query":"2026 summer sunglasses trends","max_results":5,"include_images":false}
# ✅ Tool Result:
# [{'title': '9 Trendy Sunglasses You Need 2026! Best Colors and Styles for Your Face Shape', 'content': "wearable sunglasses trends of 2026. Number three, tinted lenses. Tinted lenses are one of the most eye-catching sunglasses trends of 2026, bringing color, personality, and a touch of retro influence to everyday eyewear. Instead of relying solely on traditional dark lenses, many of this year's most fashionable sunglasses feature soft shades of amber, brown, green, blue, rose, and even subtle yellow tones that instantly make a pair feel more distinctive. The trend can be found across a wide range [...] angles. Round faces may find that slightly more structured or angular aviator styles create the most balanced effect. Number nine, chunky acetate frames. Chunky acetate frames continue to be one of the most influential sunglasses trends of 2026, offering a bold look that feels both fashionable and timeless. Unlike delicate metal frames, acetate styles make a stronger visual statement thanks to their thicker construction, substantial presence, and rich color options. This year, the trend [...] sunglasses are one of the boldest trends of 2026, bringing a fresh and modern edge to eyewear. Inspired by innovation, technology, and high-fashion runway collections, these sunglasses often feature unexpected silhouettes, sharp geometric lines, wrap-around designs, shield lenses, and sculptural details that immediately stand out. While some versions lean toward sporty aesthetics, others feel surprisingly elegant thanks to sleek materials, minimalist frames, and refined proportions. Silver", 'url': 'https://www.youtube.com/watch?v=hmmuvGdKwAs'}, {'title': 'Sunglasses Trends 2026', 'content': "Sunglasses in 2026 reflect a perfect balance between statement aesthetics and enduring design. Bold frames, sculptural silhouettes, and retro influences lead the trends, with gradient lenses and metal shades taking center stage.\n\nSome styles of sunglasses are always in. Think sleek aviators, refined cat-eye frames, and classic square sunglasses. These iconic shapes transcend trends and continue to define modern elegance, season after season. [...] From ample butterfly frames to the resurgence of oval and square sunnies, 2026 is all about statement-making eyewear. Gradient lenses add a soft, colorful twist, while bold mask designs balance subtlety and full-coverage drama. And of course, timeless metal sunglasses and oversized shades remain a staple.\n\n## Soft oval\n\nThe '90s revival is stronger than ever, with oval sunglasses dominating runways in 2026. Their timeless shape adds a touch of retro-cool to any modern look.\n\nPersol", 'url': 'https://miaburton.com/en/sunglasses/trends'}, {'title': 'The 5 Biggest Sunglasses Trends to Know for 2026', 'content': "CELINE\n\nMetal Frame 28 Sunglasses in Metal\n\nMiu Miu, Oval Sunglasses\n\nMiu Miu\n\nOval Sunglasses\n\n## Acetate\n\nThick acetate frames are a running theme from the spring/summer 2026 collections. We saw everything from sleek black styles that feel classic yet futuristic to oversize silhouettes that have an exaggerated quality.\n\nSunglasses on the 2026 runway\n\n(Image credit: Launchmetrics)\n\nSunglasses on the 2026 runway\n\n(Image credit: Launchmetrics)\n\nKhaite x Oliver Peoples, Acetate Sunglasses [...] (Image credit: Launchmetrics)\n\nCat-Eye Gold-Tone Sunglasses\n\nBOTTEGA VENETA EYEWEAR\n\nCat-Eye Gold-Tone Sunglasses\n\nMarsais Sunglasses\n\nANINE BING\n\nMarsais Sunglasses\n\n## High-Impact Color\n\nSporty, colorful frames dominated the Miu Miu runway—a brand that always sets the tone early for trends, especially when it comes to accessories. Colors ranged from blue to red to yellow, giving us a taste of the rainbow of colors we can expect to see sunglasses drop in for 2026. [...] Khaite x Oliver Peoples\n\nAcetate Sunglasses\n\nLinda 53mm Butterfly Sunglasses\n\nTOM FORD\n\nLinda 53mm Butterfly Sunglasses\n\n## Modern Cat-Eyes\n\nCat-eye sunglasses are most commonly linked to '50s fashion, but we're now seeing them reimagined in new ways. At Ralph Lauren, they're finished with delicate wire frames, while at Bottega Veneta, they're sharply angled and outfitted with gradient lenses.\n\nSunglasses on the 2026 runway\n\n(Image credit: Launchmetrics)\n\nSunglasses on the 2026 runway", 'url': 'https://www.whowhatwear.com/fashion/trends/sunglasses-trends-2026'}, {'title': 'The Best Sunglasses Trends for Men in 2026', 'content': "2026 trends\n\n# The Best Sunglasses for Men in 2026: Popular Trending Styles\n\nThis summer’s men’s sunglasses styles and trends are a versatile bunch likely to turn quite a few heads. The cool shades on the market can upgrade any guy’s look, giving him some serious style points.\n\nLike most guys, you probably have one or two pairs of classic wayfarers lying around already. But summer is the perfect time to up your game with some fresh, bold frames! [...] Heavy browline sunglasses are another hot sunglasses trend for men. You’ll find an even more prominent browline in these modern versions of the Clubmaster, giving them a thicker and manlier look.\n\nVint & York\n\nThe Vint & York Baker Sunglasses is a prime example of the thicker and manlier sunglasses frames. This retro-inspired, semi-rimless frame features square lenses and a heavy browline. The Baker men’s sunglasses look like a square version of the Club master. [...] The metallic top brow bar trend is a variation of men's original flat brow style of sunglasses.\n\nThe top metal bar is a substitute for the large, straight acetate browline. This single change transformed the look into a more elegant and modern form. The sleek and refined design perfectly mirrors the current contemporary aesthetic.\n\nVint & York", 'url': 'https://www.vintandyork.com/blogs/content/best-men-sunglasses-trends'}, {'title': 'Shield Sunglasses Are the Hottest Shades for Summer 2026', 'content': '##### Shop the Shield Sunglasses Trend\n\nStrada Sunglasses\n\nBru Eyewear\n\nStrada Sunglasses\n\n$140 at Revolve\n\nPaloma 65mm Oversize Shield Sunglasses\n\n###### Fifth & Ninth Paloma 65mm Oversize Shield Sunglasses\n\n$50 at Nordstrom\n\nRunway Wrap Sunglasses\n\n###### Tory Burch Runway Wrap Sunglasses\n\n$250 at Tory Burch\n\nShop at Amazon\n\nCredit: Tory Burch\n\nPalulu Sunglasses\n\nMaui Jim\n\nPalulu Sunglasses\n\n$309 at mauijim.com\n\nThe Luz Sunglasses\n\nJimmy Fairly\n\nThe Luz Sunglasses\n\n$148 at jimmyfairly.com [...] I know, I know—we thought we left these wraparound sunnies in the past with frosted tips and ultra-low-rise jeans. But I’ll have you know that this trend, especially in its oversized format, was seen across the runways at the spring/summer 2026 fashion shows. And, unsurprisingly, fashion girls everywhere—including none other than Jennie Kim and Rosie Huntington-Whiteley—have already been wearing the sporty, and dare I say, unsexy, trend. Honestly? The results are pretty cool. [...] I’ve seen some pretty extreme versions of fashionable women sporting the trend—Irina Shayk donned a bold, head-turning option in Cannes last year, and more recently, a girl on the subway sported actual ski goggles (I couldn’t look away). Of course, there are some subtler, more approachable styles that are perfect for your everyday occasions. From those that lean on the sporty side to give your spring and summer ’fits an edge to oversized options with tinted lenses touching on the more feminine', 'url': 'https://www.elle.com/fashion/shopping/a71017554/shield-sunglasses-trend-summer-2026'}]
# 📞 Tool Call: product_catalog_tool
# {"max_items":10}
# ✅ Tool Result:
# [{'name': 'Aviator', 'item_id': 'SG001', 'description': 'Originally designed for pilots, these teardrop-shaped lenses with thin metal frames offer timeless appeal. The large lenses provide excellent coverage while the lightweight construction ensures comfort during long wear.', 'quantity_in_stock': 23, 'price': 103}, {'name': 'Wayfarer', 'item_id': 'SG002', 'description': 'Featuring thick, angular frames that make a statement, these sunglasses combine retro charm with modern edge. The rectangular lenses and sturdy acetate construction create a confident look.', 'quantity_in_stock': 6, 'price': 92}, {'name': 'Mystique', 'item_id': 'SG003', 'description': 'Inspired by 1950s glamour, these frames sweep upward at the outer corners to create an elegant, feminine silhouette. The subtle curves and often embellished temples add sophistication to any outfit.', 'quantity_in_stock': 3, 'price': 88}, {'name': 'Sport', 'item_id': 'SG004', 'description': 'Designed for active lifestyles, these wraparound sunglasses feature a single curved lens that provides maximum coverage and wind protection. The lightweight, flexible frames include rubber grips.', 'quantity_in_stock': 11, 'price': 144}, {'name': 'Round', 'item_id': 'SG005', 'description': 'Circular lenses set in minimalist frames create a thoughtful, artistic appearance. These sunglasses evoke a scholarly or creative vibe while remaining effortlessly stylish.', 'quantity_in_stock': 10, 'price': 86}]
# ✅ Final Summary:
# Trend Analysis (Date: 2026-09-09)

# 1. Top Trends for Summer 2026  
#    • Tinted & Gradient Lenses  
#      ­– Soft color washes (amber, green, rose, blue) and two-tone/gradient lenses add a playful, retro-inspired twist.  
#    • Chunky Acetate Frames  
#      ­– Oversized, thick acetate makes a bold, statement-making look that feels both modern and timeless.  
#    • Wrap-Around/Shield Silhouettes  
#      ­– ’90s-inspired sporty shields and wrap-around shapes offer full-coverage drama and a tech-fashion edge.

# 2. Recommended Products from Internal Catalog  
#    • SG002 “Wayfarer” (Thick Acetate Frame)  
#      ­– Aligns perfectly with the chunky acetate trend; its bold angles and substantial presence meet consumer demand for statement summer eyewear.  
#    • SG004 “Sport” (Wrap-Around Lens)  
#      ­– Directly taps the shield/ wrap-around silhouette trend; lightweight, wind-protecting design appeals to active-lifestyle buyers and fashion-forward shoppers.  
#    • SG001 “Aviator” (Metal Frame with Large Lenses)  
#      ­– A perennial favorite given a modern twist by swapping in gradient or softly tinted lenses; appeals to trend-sensitive consumers seeking a metal-frame update with color.

# 3. Justification for Summer Campaign  
#    – Versatility: Together, these three styles cover the full spectrum of current tastes—from bold acetate statements to sporty shields and updated classics—allowing targeted messaging across different consumer segments.  
#    – Trend Relevance: Each style directly mirrors a top runway and street-style trend, ensuring the campaign feels fresh and culturally attuned.  
#    – Stock Availability: All items are in stock (Wayfarer: 6, Sport: 11, Aviator: 23), supporting both limited-edition drops and broader distribution.

# By featuring these three styles, the summer campaign can showcase on-trend color, form, and function—maximizing appeal and driving seasonal sales.
# ✅ Market research completed
# 🎨 Graphic Designer Agent
# ✅ Final Summary:
# <h3>Generated Image and Caption</h3>
#         <p><strong>Image Path:</strong> <code>generated_image.png</code></p>
#         <p><strong>Generated Image:</strong></p>
#         <img src="generated_image.png" alt="Generated Image" style="max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 8px; margin-top: 10px; margin-bottom: 10px;">
#         <p><strong>Prompt:</strong> A sunlit rooftop scene at golden hour with three stylish models: one wearing chunky amber acetate Wayfarer frames with bold, retro angles; another in sleek wrap-around shield sunglasses fading from emerald green to ocean blue; and a third sporting rose-tinted aviator metal frames that glimmer in the warm light. Pastel watercolor skies and soft lens flares frame their confident poses, while subtle reflections dance across glass railings. Photorealistic, high-contrast, vibrant summer palette.</p>
# 🖼️ Image generated
# ✍️ Copywriter Agent
# ✅ Final Summary:
# {"quote":"Bold Hues, Timeless Silhouettes: Your Summer Shade Story","justification":"“Bold Hues” calls out the playful tinted and gradient lenses trend, while “Timeless Silhouettes” nods to chunky acetate wayfarers and ’90s wrap-around shields. Together they mirror the image’s mix of statement frames and summer-ready colors, uniting all three key styles in one elegant campaign line."}
# 💬 Quote created
# 📦 Packaging Agent
# ✅ Tool Result:
# Summer 2026 Executive Summary (09/09/2026)

# Key Trends  
# • Tinted & Gradient Lenses  
#   – Soft color washes (amber, green, rose, blue) and two-tone fades are reintroducing a playful, retro spirit.  
# • Chunky Acetate Frames  
#   – Oversized, heavyweight acetate delivers a modern yet timeless statement.  
# • Wrap-Around/Shield Silhouettes  
#   – ’90s-inspired sporty shields provide full-coverage drama with a tech-fashion edge.

# Featured Products  
# • SG002 “Wayfarer” (Chunky Acetate)  
#   – Bold angles and substantial presence tap the oversized-frame movement.  
# • SG004 “Sport” (Wrap-Around Shield)  
#   – Lightweight, wind-protective design appeals to active-lifestyle and fashion-forward consumers.  
# • SG001 “Aviator” (Metal Frame + Gradient Lens)  
#   – A classic aviator updated with soft tints to capture the tinted-lens trend.

# Strategic Rationale  
# 1. Comprehensive Appeal  
#    The three silhouettes span bold statement, sporty functionality, and modernized classics—enabling targeted messaging across diverse segments.  
# 2. On-Trend Credibility  
#    Each model mirrors runway and street-style cues, ensuring our summer launch resonates with today’s aesthetic.  
# 3. Inventory Advantage  
#    All SKUs are in stock (Wayfarer: 6, Sport: 11, Aviator: 23), supporting both exclusive drops and broad distribution.

# By spotlighting these styles, our Summer 2026 campaign will harness the power of color, form, and function to drive engagement and maximize seasonal sales.
# 📦 Report generated: campaign_summary_2026-09-09_11-27-14.md
}


with open(results["markdown_path"], "r", encoding="utf-8") as f:
    md_content = f.read()
display(Markdown(md_content))
{
# 🕶️ Summer Sunglasses Campaign – Executive Summary
# 📊 Refined Trend Insights
# Summer 2026 Executive Summary (09/09/2026)

# Key Trends
# • Tinted & Gradient Lenses
# – Soft color washes (amber, green, rose, blue) and two-tone fades are reintroducing a playful, retro spirit.
# • Chunky Acetate Frames
# – Oversized, heavyweight acetate delivers a modern yet timeless statement.
# • Wrap-Around/Shield Silhouettes
# – ’90s-inspired sporty shields provide full-coverage drama with a tech-fashion edge.

# Featured Products
# • SG002 “Wayfarer” (Chunky Acetate)
# – Bold angles and substantial presence tap the oversized-frame movement.
# • SG004 “Sport” (Wrap-Around Shield)
# – Lightweight, wind-protective design appeals to active-lifestyle and fashion-forward consumers.
# • SG001 “Aviator” (Metal Frame + Gradient Lens)
# – A classic aviator updated with soft tints to capture the tinted-lens trend.

# Strategic Rationale

# Comprehensive Appeal
# The three silhouettes span bold statement, sporty functionality, and modernized classics—enabling targeted messaging across diverse segments.
# On-Trend Credibility
# Each model mirrors runway and street-style cues, ensuring our summer launch resonates with today’s aesthetic.
# Inventory Advantage
# All SKUs are in stock (Wayfarer: 6, Sport: 11, Aviator: 23), supporting both exclusive drops and broad distribution.
# By spotlighting these styles, our Summer 2026 campaign will harness the power of color, form, and function to drive engagement and maximize seasonal sales.

# 🎯 Campaign Visual
# Open the generated file to see

# ✍️ Campaign Quote
# Bold Hues, Timeless Silhouettes: Your Summer Shade Story

# ✅ Why This Works
# “Bold Hues” calls out the playful tinted and gradient lenses trend, while “Timeless Silhouettes” nods to chunky acetate wayfarers and ’90s wrap-around shields. Together they mirror the image’s mix of statement frames and summer-ready colors, uniting all three key styles in one elegant campaign line.

# Report generated on 2026-09-09
}