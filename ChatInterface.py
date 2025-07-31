import streamlit as st
import requests
import pandas as pd
import io

st.set_page_config(page_title="Pharma IC Agent Chat", layout="wide")
st.title("💊 Pharma IC Agent Chat")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None

# Sidebar for uploading data
st.sidebar.header("📂 Upload Historical Sales Data")
uploaded_file = st.sidebar.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.session_state.uploaded_data = df
    st.sidebar.success("✅ File uploaded successfully!")
    st.sidebar.write(df.head())  # Preview

# Chat display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Set a goal (e.g., 'Analyze Q2 drop in sales')..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare file content to send to backend
    if st.session_state.uploaded_data is not None:
        buffer = io.BytesIO()
        st.session_state.uploaded_data.to_excel(buffer, index=False)
        buffer.seek(0)
        files = {"file": ("data.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    else:
        files = {}

    # Send goal + file to CrewAI backend
    try:
        response = requests.post(
            "http://localhost:8000/agent",
            data={"goal": prompt},
            files=files if files else None,
        )
        result = response.json()["response"]
    except Exception as e:
        result = f"⚠️ Error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": result})
    with st.chat_message("assistant"):
        st.markdown(result)
