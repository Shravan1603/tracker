import streamlit as st
import pandas as pd
import plotly.express as px
from langchain.chat_models import ChatOpenAI
import sqlite3
import os
from dotenv import load_dotenv  # For environment variables
import db

# Load environment variables (e.g., OpenAI API key)
load_dotenv()

 
# Initialize OpenAI
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=os.getenv("OPENAI_API_KEY"))

conn = db.init_db() 
# Fetch task data from the database
def fetch_task_data():
    tasks =  conn.execute("""
        SELECT topic, due_date, status, progress, category, time_spent 
        FROM tasks 
        LEFT JOIN time_logs ON tasks.id = time_logs.task_id
    """).fetchall()
    return pd.DataFrame(tasks, columns=["Topic", "Due Date", "Status", "Progress", "Category", "Time Spent"])

# Generate AI-powered visualization suggestions
def get_visualization_suggestion(df):
    prompt = f"""
    Analyze the following task data and suggest the best way to visualize the user's progress:
    - Total tasks: {len(df)}
    - Completed tasks: {len(df[df['Status'] == 'Completed'])}
    - Average progress: {df['Progress'].mean():.2f}%
    - Total time spent: {df['Time Spent'].sum()} hours

    Suggest the type of visualization (e.g., line chart, pie chart, bar chart) and the metrics to include.
    """
    response = llm.invoke(prompt)
    return response.content

# Generate visualizations
def generate_visualizations(df):
    st.subheader("AI-Powered Progress Visualizations")

    # Get AI suggestion for visualization
    suggestion = get_visualization_suggestion(df)
    st.write(f"**AI Suggestion:** {suggestion}")

    # Example visualizations
    st.write("### Progress Over Time")
    df['Due Date'] = pd.to_datetime(df['Due Date'])
    df = df.sort_values(by="Due Date")
    fig1 = px.line(df, x="Due Date", y="Progress", title="Progress Over Time")
    st.plotly_chart(fig1)

    st.write("### Task Completion")
    completed = len(df[df['Status'] == 'Completed'])
    pending = len(df) - completed
    fig2 = px.pie(values=[completed, pending], names=["Completed", "Pending"], title="Task Completion")
    st.plotly_chart(fig2)

    st.write("### Time Spent per Category")
    time_per_category = df.groupby("Category")['Time Spent'].sum().reset_index()
    fig3 = px.bar(time_per_category, x="Category", y="Time Spent", title="Time Spent per Category")
    st.plotly_chart(fig3)

# Main function
def ai_progress_visualization( ):
    st.title("AI-Powered Progress Visualization")
    
    # Fetch task data
    df = fetch_task_data()
    
    if not df.empty:
        # Generate and display visualizations
        generate_visualizations(df)
    else:
        st.warning("No task data available for visualization.")
