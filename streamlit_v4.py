import streamlit as st
import html
import re
import base64
from dotenv import load_dotenv
from GoalCalculationN import calculate_goals
from Insights_Visuals import run_goal_distribution_analysis
import pandas as pd
import numpy as np
from Anomaly import detect_product1_anomalies_dynamic
from Anomaly import cross_verify_anomalies_with_fema
from Anomaly import format_disaster_impact_summary_html
import streamlit.components.v1 as components
import json
import anthropic
import os
from KPI import get_kpi_html_block
import time

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

st.set_page_config(page_title="ICAgents Goal Assistant", layout="wide")
GOAL_DATA_PATH = r"Goal Setting sanitized Data.xlsx"


# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = []

for key in ["name", "quarter", "goal", "min_territory_growth", "max_territory_growth", "calculated_df"]:
    if key not in st.session_state:
        st.session_state[key] = None


if "Insights_messages" not in st.session_state:
    st.session_state.Insights_messages = []
    
    
st.markdown("""
<style>
html, body {
    background-color: white;
    font-family: "Segoe UI", "Helvetica", sans-serif;
    color: #333;
}
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 160px;
}
.user-msg, .bot-msg {
    margin: 0.5rem 0;
    padding: 0.75rem 1rem;
    border-radius: 10px;
    max-width: 80%;
    word-wrap: break-word;
    display: flex;
    align-items: center;
    align-self: flex-start;
}
.user-msg {
    background-color: #f0f0f0;
    color: black;
}
.bot-msg {
    background-color: #fff8dc;
    color: black;
}
.icon {
    width: 30px;
    height: 30px;
    margin-right: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.user-icon {
    background-color: #dc3545;
    border-radius: 50%;
    font-weight: bold;
    color: white;
}
.bot-icon {
    background-color: #ffc107;
    border-radius: 50%;
    font-weight: bold;
    color: black;
}
.input-container {
    position: fixed;
    bottom: 1rem;
    left: 0;
    width: 100%;
    background-color: #0e1117;
    padding: 1rem 2rem;
    box-shadow: 0 -1px 8px rgba(0,0,0,0.4);
    z-index: 999;
}
.rounded-input input {
    border-radius: 2rem;
    border: 1px solid #dc3545;
    padding: 0.75rem 1rem;
    width: 100%;
    background-color: #1e1e1e;
    color: white;
}
.block-container {
    padding-bottom: 180px !important;
}
</style>
""", unsafe_allow_html=True)

# 🏢 Centered Company Logo
def image_to_base64(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


def image_file_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    
img_path = "TimeSeriesDia.png"  # or use the full path if needed
TimeSeries = image_file_to_base64(img_path)
unknown_unknown=image_file_to_base64("UnknownUnknown.png")


Timeseries_html = f"""
<div class="bot-msg">
    <div>
        <p><strong>📈 DQ Summary Visual:</strong> Here's a recent trend analysis for Brand2.</p>
        <img src="data:image/png;base64,{TimeSeries}" width="1000" style="border-radius:10px; margin-top:10px;" />
    </div>
</div>
"""


unknown_unknown_html = f"""
<div class="bot-msg">
    <div>
        <img src="data:image/png;base64,{unknown_unknown}" width="1000" style="border-radius:10px; margin-top:10px;" />
    </div>
</div>
"""
    
# 🏢 Centered Local Image
# encoded_logo = image_to_base64("logoo-removebg-preview.png")
# st.markdown(
#     f"""
#     <div style='text-align: center;'>
#         <img src='data:image/png;base64,{encoded_logo}' width='180'/>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

# Title
st.markdown("""
<h1 style='text-align: center;padding: 0px;'>Pharma360AI</h1>
<h2 style='text-align: center;padding: 0px;'>🤖 AgenticAI Solutions - Goal Calculation Assistant</h2>
<p style='text-align: center; color: gray;'>Your chatbot to help calculate quarterly goals</p>
""", unsafe_allow_html=True)
st.markdown("---")



# ✅ KPI Section
col1, col2, col3, col4 = st.columns(4)

# Optional: wrapper div for styling
st.markdown("<div class='sticky-kpi' style='margin-bottom: 1rem;'>", unsafe_allow_html=True)

# Shared style block
kpi_block = """
<div style='
    text-align: center;
    padding: 1rem;
    border-radius: 12px;
    background-color: #f9f9f9;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
'>
    <div style='font-size: 16px; font-weight: 500; color: #444;'>{title}</div>
    <div style='font-size: 24px; font-weight: bold; margin-top: 8px; color: #222;'>{value}</div>
</div>
"""

# Column 1: Current Calendar Month
with col1:
    st.markdown(kpi_block.format(title="📅 Current Calendar Month", value="May 2025"), unsafe_allow_html=True)

# Column 2: IC Territories
with col2:
    st.markdown(kpi_block.format(title="🌍 IC Territories", value="20"), unsafe_allow_html=True)

# Column 3: IC Deliverables Due
with col3:
    st.markdown(kpi_block.format(title="📂 IC Deliverables Due", value="Q3 2025 Goals"), unsafe_allow_html=True)

# Column 4: IC Summary
with col4:
    st.markdown(kpi_block.format(title="📈 Q1 2025 IC Summary", value="110% Attainment"), unsafe_allow_html=True)

# End wrapper and divider
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("---")

# Chat message container
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

def contains_html(text):
    return bool(re.search(r'<[^>]+>', text))

for sender, message in st.session_state.messages:
    if contains_html(message) and sender in ["disaster"]:
        styled_html = f"""
            <div style="
                max-width: 78%;
                background-color: #fff8dc;
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                display: flex;
                align-items: flex-start;
                box-shadow: 0px 1px 4px rgba(0, 0, 0, 0.1);
            ">
                <div style="
                    width: 30px;
                    height: 30px;
                    margin-right: 10px;
                    background-color: #ffc107;
                    border-radius: 50%;
                    font-weight: bold;
                    color: black;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">🤖</div>
                <div style="flex: 1;">{message}</div>
            </div>
            """
        components.html(styled_html, height=700)
    elif contains_html(message) and sender in ["bot"]:
        styled_html = f"""
            <div style="
                max-width: 78%;
                background-color: #fff8dc;
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                display: flex;
                align-items: flex-start;
                box-shadow: 0px 1px 4px rgba(0, 0, 0, 0.1);
            ">
                <div style="
                    width: 30px;
                    height: 30px;
                    margin-right: 10px;
                    background-color: #ffc107;
                    border-radius: 50%;
                    font-weight: bold;
                    color: black;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">🤖</div>
                <div style="flex: 1;">{message}</div>
            </div>
            """
        components.html(styled_html, height=300)
    elif contains_html(message) and sender in ["DQ"]:
        components.html(message, width=1000,height=300)    
    elif contains_html(message) and sender == "image":
       components.html(message, height=200, width=1000)
    else:
        role_class = "user-msg" if sender == "user" else "bot-msg"
        icon = "🙎‍♂️" if sender == "user" else "🤖"
        icon_class = "user-icon" if sender == "user" else "bot-icon"

        # Render standard escaped message
        safe_message = html.escape(message)
        st.markdown(f"""
            <div class="{role_class}">
                <div class="icon {icon_class}">{icon}</div>
                {safe_message}
            </div>
        """, unsafe_allow_html=True)
        
if "suggestion_used" not in st.session_state:
    st.session_state.suggestion_used = False
            
df = st.session_state.get("calculated_df")
if df is not None and not df.empty:
    with st.spinner("⚙️ Calculating goals, please wait..."):
        st.markdown("### 📊 Calculated Goals")
        st.dataframe(df, use_container_width=True)

    with st.spinner("🤖 Analyzing data and generating insights..."):
        run_goal_distribution_analysis(df)
        
st.markdown("""
    <style>
    div.stButton > button {
        border-radius: 20px;
        background-color: #f1f3f5;
        color: #333;
        border: 1px solid #d3d3d3;
        font-size: 14px;
        padding: 0.4rem 1.2rem;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)
        
st.markdown('<h4 style="padding-left:10px">ASK G-IIC (GILEAD INTELLIGENCE INCENTIVE COMPENSATION)</h4>', unsafe_allow_html=True)

with st.container(border=True):
    # Outer styled box
    # st.markdown("""
    #     <div style='
    #         background-color: #f9f9f9;
    #         padding: 1.5rem;
    #         border-radius: 12px;
    #         box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    #         margin-bottom: 1rem;
    #     '>
    # """, unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        cols = st.columns([0.9, 0.1])
        with cols[0]:
            user_input = st.text_input(
                "", placeholder="Ask your question here...",
                label_visibility="collapsed", key="user_text"
            )
        with cols[1]:
            submitted = st.form_submit_button("➤")

    # Suggested questions (inside the box)
    if not st.session_state.get("suggestion_used", False):
        st.markdown("""
            <div style='text-align: center; font-size: 20px; font-weight: 500; margin-top: 1rem;'>
                💡 Try any of these to get started
            </div>
            """, unsafe_allow_html=True)
        suggested_questions = [
            "Calculate goal for Q3?",
            "Describe goal setting methodology",
            "Evaluate impact due to FEMA emergencies",
            "Show input data readiness for goal setting"
        ]

        st.markdown("<div style='margin-top: 1rem; text-align: center;'>", unsafe_allow_html=True)
        q_cols = st.columns(len(suggested_questions))
        for i, q in enumerate(suggested_questions):
            with q_cols[i]:
                if st.button(q, key=f"suggestion_{i}"):
                    #st.session_state.messages.append(("user", q))
                    st.session_state.suggestion_used = True
                    user_input=q
                    submitted=True
                    #st.rerun()
        

      # Close outer container


# if submitted and user_input:
#     st.session_state.messages.append(("user", user_input))
#     st.rerun()


# On user submit
if submitted and user_input:
    st.session_state.messages.append(("user", user_input))

    claude_messages = [
        {"role": "user" if sender == "user" else "assistant", "content": msg}
        for sender, msg in st.session_state.messages
        if sender not in ["DQ","image"]
    ]

    claude_prompt = f"""
    You are a helpful assistant that helps users calculate quarterly sales goals.

    Your job is to extract structured information from the conversation.

    ### Required fields:
    - name: the user's name (if mentioned)
    - quarter: sales quarter (Q3 or Q4 only)
    - goal: national goal amount (number)
    - min_territory_growth: minimum expected territory growth percentage (number)
    - max_territory_growth: maximum expected territory growth percentage (number)
    - product_weights: e.g., {{ "Product 2": 60, "Product 3": 40 }}, or null if not confirmed
    - baseline_period: a number between 1 and 6 (months), or null if not confirmed
    - exclude_disaster_months: true, false, or null (depending on whether user confirmed to exclude FEMA-impacted months from baseline)
    - intent: one of "goal_calculation", "general_greeting", "out_of_scope"
    - suggestion: a friendly next message to the user

    ### Behavior:
    - Begin goal calculation only when these are present:
        - quarter, goal, min/max territory growth
        - product_weights, baseline_period
        - exclude_disaster_months is either true or false
    - If product_weights or baseline_period is missing, prompt like:
        - 🧮 "Please confirm product weights — default is Product 2: 60%, Product 3: 40%. Would you like to proceed with these or update them?"
        - 🕒 "Please confirm baseline period (3 or 6 months). For Q1/Q2, 6 months was used. Do you want to keep it or change it?"

    - If FEMA-related disaster months were shown, wait for user's input about exclusion:
        - If user says something like "Yes, exclude disaster months", set exclude_disaster_months = true
        - If user says "No, include all months", set exclude_disaster_months = false
        - If no decision yet, set it to null and ask:
        - ⚠️ "Would you like to exclude the disaster-affected months from the baseline calculation?"

    - If quarter is Q1 or Q2, respond with:
    - "Sales data already exists for Q1 and Q2. Please calculate goals for Q3 or Q4."

    - If user greets, respond politely and ask for required fields.

    - If the topic is unrelated to sales goal calculation, respond:
    - "This is outside of sales goal calculation. I can't help with that."

    ### Respond ONLY with a valid JSON object:
    {{
    "name": "<name or null>",
    "quarter": "<quarter or null>",
    "goal": "<goal or null>",
    "min_territory_growth": <number or null>,
    "max_territory_growth": <number or null>,
    "product_weights": {{ "Product 2": 60, "Product 3": 40 }} or null,
    "baseline_period": <1–6 or null>,
    "exclude_disaster_months": true | false | null,
    "intent": "<goal_calculation | general_greeting | out_of_scope>",
    "suggestion": "<next thing you want the user to do>"
    }}

    ### Conversation:
    {json.dumps(claude_messages, indent=2)}
    """

    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=512,
            temperature=0,
            messages=[{"role": "user", "content": claude_prompt}]
        )

        raw_output = response.content[0].text.strip()
        clean_json = re.sub(r'[\x00-\x1F\x7F]', '', raw_output)
        data = json.loads(clean_json)
        #st.json(clean_json)
        #print(clean_json)

        parsed = {
            "name": data.get("name", "User"),
            "quarter": data.get("quarter"),
            "goal": data.get("goal"),
            "min_territory_growth": data.get("min_territory_growth"),
            "max_territory_growth": data.get("max_territory_growth"),
            "product_weights": data.get("product_weights"),
            "baseline_period": data.get("baseline_period"),
            "exclude_disaster_months": data.get("exclude_disaster_months"),
            "intent": data.get("intent", "unknown"),
            "suggestion": data.get("suggestion")
        }

        for key, value in parsed.items():
            st.session_state[key] = value

        if parsed["intent"] == "goal_calculation" and all([
            parsed["quarter"], parsed["goal"],
            parsed["min_territory_growth"], parsed["max_territory_growth"]
        ]):
            st.session_state["pending_goal_data"] = parsed

            if parsed.get("product_weights") is not None:
                st.session_state["proposed_weights"] = parsed["product_weights"]
                st.session_state["product_weights_confirmed"] = True
            else:
                st.session_state["product_weights_confirmed"] = False
                bot_response = (
                "📦 For goals to be assigned based on growth potential, please confirm product weights "
                "(e.g., Product 2: 60%, Product 3: 40%). "
                "**Proceed with the default, or would you like to update them?**"
            )
            if parsed.get("baseline_period") is not None and 1 <= parsed["baseline_period"] <= 6:
                st.session_state["proposed_baseline"] = parsed["baseline_period"]
                st.session_state["baseline_confirmed"] = True
            else:
                st.session_state["baseline_confirmed"] = False
                if parsed.get("baseline_period") and parsed["baseline_period"] > 6:
                    bot_response = "⚠️ Baseline period must be 6 months or less. Please provide a number from 1 to 6."
                else:
                    bot_response = "🕒 While calculating the goal for Q1 and Q2, a 6-month baseline period was considered. Would you like to change it or proceed with this?"
            
            if parsed.get("baseline_period") is not None and parsed.get("product_weights") is None:
                # Row 1
                kpi_html_block = get_kpi_html_block()

                # Only add once
                if "kpi_snapshot_shown" not in st.session_state:
                    st.session_state.messages.append(("bot", "🧾 DQ Summary: Based on the IC inputs provided, here is a snapshot of the data quality signals we've identified."))
                    st.session_state.messages.append(("DQ", kpi_html_block))
                    st.session_state["kpi_snapshot_shown"] = True
                if "dq_image_shown" not in st.session_state:
                    st.session_state.messages.append(("image", Timeseries_html))
                    st.session_state["dq_image_shown"] = True
                    
                if "unknown_unknown_shown" not in st.session_state:
                    st.session_state.messages.append(("image", unknown_unknown_html))
                    st.session_state["unknown_unknown_shown"] = True          

            if st.session_state.get("product_weights_confirmed") and st.session_state.get("baseline_confirmed"):
                try:
                    goal_value = pd.to_numeric(parsed["goal"], errors="coerce")
                    min_growth = pd.to_numeric(parsed["min_territory_growth"], errors="coerce")
                    max_growth = pd.to_numeric(parsed["max_territory_growth"], errors="coerce")
                    weights = st.session_state["proposed_weights"]
                    baseline = st.session_state["proposed_baseline"]
                    
                    
                    # ✅ Load and verify anomalies before calculating goals
                    sales_df=pd.read_excel("Goal Setting sanitized Data.xlsx", sheet_name='Input Sales_Anomaly_Introduced')
                    fema_df=pd.read_excel("ZIP_to_Territory_with_FEMA_Data.xlsx",sheet_name="2025_ZIP_to_Territory")
                    anomalies_df = detect_product1_anomalies_dynamic(sales_df)
                    verified_anomalies = cross_verify_anomalies_with_fema(anomalies_df, fema_df)
                    

                    if verified_anomalies["Disaster Match"].any():
                        if parsed["exclude_disaster_months"] is None:
                            # Ask for confirmation only once
                            if not st.session_state.get("disaster_message_shown"):
                                disaster_summary = format_disaster_impact_summary_html(verified_anomalies, sales_df)
                                st.session_state.messages.append(("disaster", disaster_summary))
                                st.session_state["disaster_message_shown"] = True
                                st.rerun()

                        # Set exclude_months based on user response
                        if parsed["exclude_disaster_months"] is True:
                            exclude_months =  verified_anomalies[verified_anomalies['Disaster Match']==True]["Month"].unique().tolist()
                        else:
                            exclude_months = None
                    else:
                        exclude_months = None
                    #st.write(exclude_months)
                    df = calculate_goals(
                        goal_value,
                        GOAL_DATA_PATH,
                        min_growth,
                        max_growth,
                        product_weights=weights
                        # baseline_months=baseline
                    )
                    st.session_state["calculated_df"] = df
                    name = parsed.get("name", "User") or "User"
                    formatted_weights = ', '.join([f"{k}: {v}%" for k, v in weights.items()])
                    
                    bot_response = f"""
                    <div style='background-color: #fff8dc; padding: 1.5rem; border-radius: 10px; font-family: sans-serif; line-height: 1.6;'>
                        <p>✅ Hi <strong>{name}</strong>, I've calculated your goals for <strong>{parsed['quarter']}</strong>.</p>
                        <ul style='list-style: none; padding-left: 0;'>
                            <li>🏆 <strong>National Goal:</strong> {goal_value:,}</li>
                            <li>📈 <strong>Territory Growth Range:</strong> {min_growth}% – {max_growth}%</li>
                            <li>🧮 <strong>Product Weights:</strong> {formatted_weights}</li>
                            <li>🕒 <strong>Baseline Period:</strong> {baseline} months</li>
                        </ul>
                        <p>📊 Please refer to the table below for the calculated goals.</p>
                    </div>
                    """

                except Exception as e:
                    bot_response = f"❌ Error during goal calculation: {e}"

        elif parsed["intent"] == "general_greeting":
            name = parsed.get('name', 'User') or 'User'
            bot_response = (
                f"👋 Hello {name}! Would you like to calculate goals for Q3 or Q4?\n"
                "Please tell me your quarter, national goal, and territory growth range."
            )
        else:
            bot_response = parsed["suggestion"]

    except json.JSONDecodeError as e:
        bot_response = f"❌ Claude response could not be parsed: {e}"
    except Exception as e:
        bot_response = f"❌ Claude API Error: {e}"

    st.session_state.messages.append(("bot", bot_response))
    #time.sleep(10)
    st.rerun()

