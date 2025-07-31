import plotly.express as px
import plotly.graph_objects as go
import json
import re
import pandas as pd
import streamlit as st
import anthropic
from dotenv import load_dotenv
from GoalCalculationN import calculate_goals
import os
import numpy as np

# Load API Key
load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Initialize session state
if "Insights_messages" not in st.session_state:
    st.session_state.Insights_messages = []

# # Clear messages
# if st.button("🧹 Clear chat"):
#     st.session_state.messages = []

def previous_quarter_sales():
    df = pd.read_excel('C:\IC Agents\crewai\icagents\Goal Setting sanitized Data.xlsx', sheet_name='Input Sales')  # Assuming header starts at row 4

    # Clean column names
    df.columns = df.columns
    columns_to_sum = [
        "Product 1 R12 Apr",
        "Product 1 R12 May",
        "Product 1 R12 Jun"
    ]

    df["Product 1 Q2"] = df[columns_to_sum].sum(axis=1)
    df=df[["Territory", "Territory Name", "Product 1 Q2"]]
    
    return df


def run_goal_distribution_analysis(calculated_df):
    # Step 1: Summarize the dataset
    dataset_summary = (
        f"Columns: {list(calculated_df.columns)}\n"
        f"Shape: {calculated_df.shape}\n"
        f"Descriptive Statistics:\n{calculated_df.describe().to_string()}"
        f"\nRegion by Goal:\n{calculated_df.groupby("Region Name")["Final Goal (cartons)"].sum().reset_index()}"
        f"\nTerritory by Goal:\n{calculated_df.groupby("Territory Name")["Final Goal (cartons)"].sum().reset_index()}"
    )

    # Step 2: Generate question
    prompt_q = f"""
    You are a data analysis assistant.

    Given the following dataset summary focused on goals assigned to each Territory, write ONE important plain-language question that highlights a key pattern, concern, or insight an end user should be aware of.

    The question must:
    - Be based only on the dataset summary provided.
    - Focus specifically on the "Final Goal (cartons)" column as it relates to "Territory Name".
    - Highlight something meaningful, surprising, or worth further attention (e.g., large disparities, top/bottom performers, unexpected trends).
    - Be phrased in clear, non-technical language for business users.

    Use ONLY the column names in the dataset.
    Return ONLY JSON in the following format:
    {{
    "question": "your question here"
    }}

    Dataset Summary:
    {dataset_summary}
    """

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt_q}],
            max_tokens=300
        )
        parsed = json.loads(re.sub(r"[\x00-\x1F\x7F]", "", response.content[0].text.strip()))
        question = parsed.get("question", "")
    except Exception as e:
        st.session_state.Insights_messages.append(("bot", f"⚠️ Failed to generate the question: {e}"))
        return

    if not question:
        st.session_state.Insights_messages.append(("bot", "⚠️ Couldn't generate a question about goal distribution."))
        return

    # Step 3: Determine chart configuration
    viz_prompt = f"""
    You are a data visualization expert.

    Your task is to analyze a dataset and suggest the best chart to **show how goals or targets are distributed across regions or territories**.

    Here is the user's question:
    "{question}"

    Here are the available dataset columns:
    {list(calculated_df.columns)}

    Please output ONLY a JSON object with the following structure:
    {{
    "title": "A concise, human-readable chart title summarizing the question",
    "chart_type": "Recommended chart type (e.g., 'bar', 'column', 'pie', etc.)",
    "x": "Column name to use for the x-axis (e.g., 'Region', 'Territory')",
    "y": "Column name to use for the y-axis (e.g., 'Final Goal (cartons)', 'Adjusted Preliminary Goal')"
    }}

    The goal is to help a business user understand how goals are allocated by region or territory. Choose fields that best represent this distribution.
    """


    try:
        viz_response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": viz_prompt}],
            max_tokens=300
        )
        chart_cfg = json.loads(re.sub(r"[\x00-\x1F\x7F]", "", viz_response.content[0].text.strip()))
    except Exception as e:
        st.session_state.Insights_messages.append(("bot", f"⚠️ Failed to get chart config: {e}"))
        return

    # Step 4: Generate the chart
    x_col = chart_cfg.get("x", calculated_df.columns[0])
    y_col = chart_cfg.get("y", calculated_df.columns[1])
    chart_type = chart_cfg.get("chart_type", "bar")
    title = chart_cfg.get("title", "Goal Distribution Chart")
    
    goal_col = "Final Goal (cartons)"
    territory_col = "Territory Name"
    
    top_10 = calculated_df.nlargest(10, goal_col)
    bottom_10 = calculated_df.nsmallest(10, goal_col)
    calculated_df = pd.concat([top_10, bottom_10]).sort_values(by=goal_col, ascending=False).reset_index(drop=True)
    
    if x_col.lower()=="region":
        x_col="Region Name"
    elif x_col.lower()=="territory" or x_col.lower()=="territory id" or x_col.lower()=="territory_id":
        x_col="Territory Name"    
    
    if y_col.lower()=="region":
        y_col="Region Name"
    elif y_col.lower()=="territory" or y_col.lower()=="territory id" or y_col.lower()=="territory_id":
        y_col="Territory Name"        
    
    #st.write(chart_type)  
    chart_type="bar"  
    calculated_df['Capped Amount'] = calculated_df['Growth%'] - calculated_df['Capped Growth%']

    if chart_type == "bar" or chart_type == "column":
        previous_df = previous_quarter_sales()

        # Optional merge with previous data if needed
        # merged_df = calculated_df.merge(
        #     previous_df[['Territory', 'Product 1 Q2']],
        #     on='Territory',
        #     how='inner'
        # )

        # Stacked Bar using go for capped logic
        if chart_type == "bar":
            total_growth = (calculated_df['Capped Growth%'] + calculated_df['Capped Amount']).to_numpy().reshape(-1, 1)
            fig = go.Figure(data=[
                go.Bar(
                    name='Capped Growth%',
                    x=calculated_df['Territory Name'],
                    y=calculated_df['Capped Growth%'],
                    marker_color='blue',
                    hovertemplate='Capped Growth: %{y:.2f}%<extra></extra>'
                ),
                go.Bar(
                    name='Total Growth%',
                    x=calculated_df['Territory Name'],
                    y=calculated_df['Capped Amount'],
                    marker_color='orange',
                    customdata=total_growth,
                    hovertemplate='Total Growth: %{customdata:.2f}%<extra></extra>'
                )
            ])
            fig.update_layout(
                title='Total vs Capped Growth % by Territory',
                xaxis_title='Territory',
                yaxis_title='Growth %',
                barmode='stack'
            )
        elif chart_type == "column":
            fig = go.Figure(data=[
                go.Bar(name='Capped Growth%', y=calculated_df['Territory Name'], x=calculated_df['Capped Growth%'], marker_color='blue', orientation='h'),
                go.Bar(name='Total Growth%', y=calculated_df['Territory Name'], x=calculated_df['Capped Amount'], marker_color='orange', orientation='h')
            ])
            fig.update_layout(
                title='Total vs Capped Growth % by Territory',
                xaxis_title='Growth %',
                yaxis_title='Territory',
                barmode='stack'
            )

    elif chart_type == "pie":
        fig = px.pie(calculated_df, names=x_col, values=y_col, title=title)

    elif chart_type == "line":
        fig = px.line(calculated_df, x=x_col, y=y_col, title=title)

    else:
        fig = px.bar(calculated_df, x=x_col, y=y_col, title=title)
    #st.session_state.Insights_messages.append(("bot", f"📊 **{question}**"))
    # if "notes" in chart_cfg:
    #     st.session_state.Insights_messages.append(("bot", f"📌 *Note: {chart_cfg['notes']}*"))
    st.plotly_chart(fig, use_container_width=True)

    # # Step 5: Generate insights
    # insight_prompt = f"""
    # You are a data analyst.

    # Analyze the following data and chart that visualizes how goals (Final Goal in cartons) are distributed across territories and how they compare to the previous quarter.

    # **Your task:**
    # - Identify meaningful patterns or disparities in current goal distribution across territories.
    # - Highlight changes (growth or decline) compared to the previous quarter's goals.
    # - Provide root causes for the biggest increases or decreases.

    # Data fields:
    # - "Territory Name": the sales territory.
    # - "Final Goal (cartons)": the current quarter's goal.
    # - "Product 1 Q2": the previous quarter's goal for the same territory.
    # - "Growth (%)": the percentage change in goal vs last quarter.

    # Data:
    # {calculated_df].to_string(index=False)}

    # Return exactly:
    # Insights:
    # 1. ...
    # 2. ...
    # 3. ...

    # Growth Analysis:
    # - ...
    # - ...

    # Root Cause Analysis:
    # - ...
    # - ...
    # """

    # try:
    #     insight_response = client.messages.create(
    #         model="claude-3-5-sonnet-20241022",
    #         messages=[{"role": "user", "content": insight_prompt}],
    #         max_tokens=800
    #     )
    #     insights_text = insight_response.content[0].text.strip()
    #     st.session_state.Insights_messages.append(("bot", insights_text))
    # except Exception as e:
    #     st.session_state.Insights_messages.append(("bot", f"⚠️ Couldn't generate insights: {e}"))
    # for role, msg in st.session_state.Insights_messages:
    #     if role == "bot":
    #         st.markdown(msg)
    
    
        

# # #Load data
# df = calculate_goals(5600, "C:/IC Agents/crewai/icagents/Goal Setting sanitized Data.xlsx", -1.0,1.0)

# # UI control to run the analysis
# if st.button("▶️ Run Goal Distribution Analysis"):
#     run_goal_distribution_analysis(df)

# # Display messages from the assistant
# for role, msg in st.session_state.messages:
#     if role == "bot":
#         st.markdown(msg)
