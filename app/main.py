import streamlit as st
from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
import sqlite3
import datetime
import hashlib  # For password hashing
import secrets  # For generating salt
import pandas as pd  # For exporting data
import plotly.express as px  # For progress visualization
import time  # For time tracking
import os
from dotenv import load_dotenv  # For environment variables
from quiz import ai_quiz_generation
import db

# Load environment variables (e.g., OpenAI API key)
load_dotenv()

conn = db.init_db()

# OpenAI Agent Setup
try:
    llm = ChatOpenAI(model_name="gpt-4", openai_api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    st.error(f"Failed to initialize OpenAI: {str(e)}")
    st.stop()

memory = ConversationBufferMemory(memory_key="chat_history")

# Password Hashing with hashlib
def hash_password(password):
    salt = secrets.token_hex(16)  # Generate a random salt
    salted_password = salt + password
    hashed_password = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    return f"{salt}:{hashed_password}"

def check_password(hashed_password, user_password):
    salt, stored_hash = hashed_password.split(':')
    salted_password = salt + user_password
    computed_hash = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    return computed_hash == stored_hash

# User Authentication
def register_user(username, password):
    try:
        hashed_password = hash_password(password)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("Username already exists. Please choose a different username.")
        return False
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")
        return False

def authenticate_user(username, password):
    try:
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        if user and check_password(user[1], password):
            return user[0]
        return None
    except Exception as e:
        st.error(f"Error authenticating user: {str(e)}")
        return None

# Session State Management
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'points' not in st.session_state:
    st.session_state['points'] = 0  # Gamification points


# Styling with CSS
st.markdown("""
    <style>
    body {
        background-color: #f4f4f4;
        color: #333333;
    }
    .sidebar .sidebar-content {
        background-color: #37474f;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #4CAF50;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

 

# User Authentication UI
if not st.session_state['logged_in']:
    st.title("AI-Powered Learning Tracker")
    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if menu == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user_id = authenticate_user(username, password)
            if user_id:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success(f"Welcome {username}!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

    elif menu == "Register":
        st.subheader("Register")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        if st.button("Register"):
            if register_user(new_user, new_password):
                st.success("Account created successfully! Please login.")

else:
    # Dashboard (Visible only after login)
    st.sidebar.header("Dashboard")
    panel_option = st.sidebar.radio("Select Option", ["Today's Tasks", "Add Task", "Time Slots", "Generate Schedule", "Export Data", "Gamification", "AI Insights", "AI Quiz Generation"])

    # Today's Tasks
    if panel_option == "Today's Tasks":
        st.subheader("Your Tasks for Today")
        try:
            tasks = conn.execute("SELECT topic, status, progress, priority, category FROM tasks WHERE status='Pending' ORDER BY priority DESC").fetchall()
            if tasks:
                # Summary Card
                total_tasks = len(tasks)
                completed_tasks = sum(1 for task in tasks if task[2] == 100)
                pending_tasks = total_tasks - completed_tasks

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Tasks", total_tasks)
                with col2:
                    st.metric("Completed Tasks", completed_tasks)
                with col3:
                    st.metric("Pending Tasks", pending_tasks)

                # Task List in Tabular Format
                st.write("### Task List")
                task_df = pd.DataFrame(tasks, columns=["Topic", "Status", "Progress", "Priority", "Category"])
                
                # Add a color-coded priority column
                def priority_color(priority):
                    if priority == "High":
                        return "🔴 High"
                    elif priority == "Medium":
                        return "🟠 Medium"
                    elif priority == "Low":
                        return "🟢 Low"
                    else:
                        return priority
                
                task_df["Priority"] = task_df["Priority"].apply(priority_color)
                
                # Display the table
                st.dataframe(task_df, use_container_width=True)

                # Visualizations
                st.write("### Task Distribution")
                pri_col1, cat_col2 = st.columns(2)
                with pri_col1:
                    priority_counts = task_df.groupby("Priority").size().reset_index(name="Count")
                    fig1 = px.pie(priority_counts, values="Count", names="Priority", title="Tasks by Priority")
                    st.plotly_chart(fig1)
                
                with cat_col2:
                    category_counts = task_df.groupby("Category").size().reset_index(name="Count")
                    fig2 = px.bar(category_counts, x="Category", y="Count", title="Tasks by Category", color="Category")
                    st.plotly_chart(fig2)

            else:
                st.write("No tasks for today.")
        except Exception as e:
            st.error(f"Error fetching tasks: {str(e)}")


    # AI Progress Visualization
    if panel_option == "AI Quiz Generation":
        ai_quiz_generation( )

    # Add Task
    if panel_option == "Add Task":
        st.subheader("Add a New Task")
        topic = st.text_input("Enter Topic")
        due_date = st.date_input("Due Date")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        category = st.text_input("Category (e.g., Math, Programming)")
        recurrence = st.selectbox("Recurrence", ["None", "Daily", "Weekly", "Monthly"])
        if st.button("Save Task"):
            try:
                conn.execute("INSERT INTO tasks (topic, subtopics, due_date, status, priority, progress, category, recurrence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (topic, "", due_date, "Completed", priority, 0, category, recurrence))
                conn.commit()
                st.success("Task saved successfully!")
            except Exception as e:
                st.error(f"Error saving task: {str(e)}")



    # Time Slots
    if panel_option == "Time Slots":
        st.subheader("Set Available Time Slots")
        day = st.date_input("Select Date")
        slot = st.text_input("Enter Time Slot (e.g., 10:00 AM - 11:00 AM)")
        if st.button("Save Slot"):
            try:
                conn.execute("INSERT INTO slot (date, slot) VALUES (?, ?)", (day, slot))
                conn.commit()
                st.success("Time slot saved!")
            except Exception as e:
                st.error(f"Error saving time slot: {str(e)}")


     # Schedule Task
    if panel_option == "Generate Schedule":
        st.title("📅 AI-Powered Task Scheduler")

        # Input: Task details
        tasks = conn.execute("SELECT id, topic, due_date, category, status, progress, priority FROM tasks WHERE status='Pending' ORDER BY priority DESC").fetchall()
        task_options = {task[1]: task[0] for task in tasks}  # Create a mapping of task names to task IDs
        selected_task_name = st.selectbox("Select Task", list(task_options.keys()))  # Display task names
        selected_task_id = task_options[selected_task_name]  # Get the corresponding task ID

        # Fetch task details for the selected task
        query = """
            SELECT topic, due_date, status, progress, priority, category 
            FROM tasks 
            WHERE id = ? AND status = 'Pending' 
            ORDER BY priority DESC
        """
        result = conn.execute(query, (selected_task_id,)).fetchall()

        # Extract the due_date if the result isn't empty
        if result:
            due_date = st.date_input("Select Due Date", value=datetime.datetime.strptime(result[0][1], "%Y-%m-%d").date())
            category = st.text_input("Category", value=result[0][5])

        # Fetch slots
        query_slot = """
            SELECT date, slot 
            FROM slot 
            WHERE date = ? 
            ORDER BY slot DESC
        """    
        result_slot = conn.execute(query_slot, (due_date,)).fetchall()

        if st.button("Generate Schedule") and selected_task_name:
            prompt = f"""
            Create a detailed breakdown of the {category} - '{selected_task_name}' with subtopics.
            Assign estimated durations to each subtopic, and create a schedule to complete it by {due_date}.
            and check the availbe slots - {result_slot} for the day.

            Format the output as a table with exactly 3 columns:
            1. Subtopic: The name of the subtopic.
            2. Duration: The estimated duration (e.g., 30 minutes, 1 hour).
            3. Suggested Time Slot: A suggested time slot (e.g., 10:00 AM - 10:30 AM).

            Separate columns using the '|' symbol. For example:
            Subtopic | Duration | Suggested Time Slot
            ---------|----------|--------------------
            Introduction | 30 minutes | 10:00 AM - 10:30 AM
            Practice Problems | 1 hour | 10:30 AM - 11:30 AM
            Review | 30 minutes | 11:30 AM - 12:00 PM
            """
            try:
                gen_col, timer_col = st.columns(2)
                with st.spinner("Generating schedule..."):   
                    response = llm.invoke(prompt)
                    st.success("✅ Schedule generated!")
                                     
                

                # Display the schedule
                st.markdown("### 📌 Your AI-Generated Schedule")

                # Parse the schedule text into a table
                schedule_data = [line.split('|') for line in response.content.strip().split('\n') if '|' in line]

                # Ensure each row has exactly 3 columns
                schedule_data = [row[:3] for row in schedule_data if len(row) >= 3]

                # Create the DataFrame
                df = pd.DataFrame(schedule_data, columns=["Subtopic", "Duration", "Time Slot"])

                # Add emojis and style
                df['Subtopic'] = '🔹 ' + df['Subtopic']

                # Display the DataFrame
                st.dataframe(df.style.set_properties(**{'background-color': '#f0f0f0', 'color': '#333333', 'border': '1px solid #ddd'}))

                    
                    # Save schedule to DB
                if st.button("💾 Save Schedule"):
                    try:
                        cursor = conn.cursor()
                        for row in df.itertuples(index=False):
                            # Access row values using indices (since itertuples returns named tuples)
                            date_str = str(due_date)  # Convert due_date to string
                            time_slot = row[2]  # Access the 'Time Slot' column by index
                            subtopic = row[0]  # Access the 'Subtopic' column by index

                            # Insert into the schedule table
                            cursor.execute("""
                                INSERT INTO schedule (date, slot, task_id, subtopics)
                                VALUES (?, ?, ?, ?)
                            """, (date_str, time_slot, selected_task_name, subtopic))
                            conn.commit()
                        
                        
                        st.success("📁 Schedule saved to database!")
                    except sqlite3.Error as e:
                        st.error(f"❗ Error saving schedule to database: {str(e)}")
                    except Exception as e:
                        st.error(f"❗ An unexpected error occurred: {str(e)}")
            except Exception as e:
                st.error(f"❗ Error generating schedule: {str(e)}")

        # Display saved schedule
        st.markdown("### 🗂 Saved Schedules")
        cur = conn.cursor()

        # Fetch saved schedules with task names by joining with the tasks table
        cur.execute("""
            SELECT s.date, s.slot, t.topic AS task, s.subtopics 
            FROM schedule s
            JOIN tasks t ON s.task_id = t.id
        """)
        saved_schedules = cur.fetchall()

        if saved_schedules:
            saved_df = pd.DataFrame(saved_schedules, columns=["Date", "Time Slot", "Task", "Subtopics"])
            st.dataframe(saved_df.style.set_properties(**{'background-color': '#e8f5e9', 'color': '#2e7d32', 'border': '1px solid #ddd'}))
        else:
            st.info("No saved schedules yet. Generate one above!")

    # Export Data
    if panel_option == "Export Data":
        st.subheader("Export Tasks to CSV")
        try:
            tasks = conn.execute("SELECT * FROM tasks").fetchall()
            df = pd.DataFrame(tasks, columns=["ID", "Topic", "Subtopics", "Due Date", "Status", "Priority", "Progress", "Category", "Recurrence"])
            st.download_button("Export Tasks", df.to_csv(index=False), file_name="tasks.csv")
        except Exception as e:
            st.error(f"Error exporting data: {str(e)}")

    # Gamification
    if panel_option == "Gamification":
        st.subheader("Earn Points for Completing Tasks")
        st.write(f"Total Points: {st.session_state['points']}")
        if st.button("Complete Task"):
            st.session_state['points'] += 10
            st.success(f"You earned 10 points! Total points: {st.session_state['points']}")

    # AI Insights
    if panel_option == "AI Insights":
        st.subheader("AI-Powered Insights")
        tasks = conn.execute("SELECT topic, due_date, status, priority, progress FROM tasks").fetchall()
        # Timer Section
        if tasks:
            task_id = st.selectbox("Select Task to Track Time", [task[0] for task in tasks])
            
            # Initialize session state for timer
            if 'start_time' not in st.session_state:
                st.session_state['start_time'] = None
            if 'elapsed_time' not in st.session_state:
                st.session_state['elapsed_time'] = 0

            # Start Timer
            if st.button("Start Timer", disabled=st.session_state['start_time'] is not None):
                st.session_state['start_time'] = time.time()
                st.session_state['elapsed_time'] = 0
                st.success("Timer started!")

            # Display Elapsed Time
            if st.session_state['start_time']:
                elapsed_time = int(time.time() - st.session_state['start_time'])
                st.session_state['elapsed_time'] = elapsed_time
                st.write(f"⏱️ Elapsed Time: {elapsed_time}" + " seconds")

            # Stop Timer
            if st.button("Stop Timer", disabled=st.session_state['start_time'] is None):
                if st.session_state['start_time']:
                    end_time = time.time()
                    time_spent = int(end_time - st.session_state['start_time'])
                    try:
                        conn.execute("""
                            INSERT INTO time_logs (task_id, start_time, end_time, time_spent)
                            VALUES (?, ?, ?, ?)
                        """, (task_id, st.session_state['start_time'], end_time, time_spent))
                        conn.commit()
                        st.success(f"✅ Time tracked: { (time_spent) } seconds")
                        st.session_state['start_time'] = None
                    except sqlite3.Error as e:
                        st.error(f"❗ Error saving time log: {str(e)}")
                    except Exception as e:
                        st.error(f"❗ An unexpected error occurred: {str(e)}")
                else:
                    st.error("Timer not started!")

            # Helper function to format time in HH:MM:SS
            def format_time(seconds):
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours:02}:{minutes:02}:{seconds:02}"
        
            # Fetch data for insights
            
            time_logs = conn.execute("SELECT task_id, time_spent FROM time_logs").fetchall()
            
            if tasks and time_logs:
                # Prepare data for OpenAI
                task_data = "\n".join([f"Task: {task[0]}, Due: {task[1]}, Status: {task[2]}, Priority: {task[3]}, Progress: {task[4]}%" for task in tasks])
                time_data = "\n".join([f"Task ID: {log[0]}, Time Spent: {log[1]} seconds" for log in time_logs])
                
                # Generate insights using OpenAI
                if st.button("Generate Insights"):
                    prompt = f"""
                    Analyze the following task and time tracking data to provide insights:
                    
                    Tasks:
                    {task_data}
                    
                    Time Logs:
                    {time_data}
                    
                    Provide insights on:
                    1. Peak productivity hours.
                    2. Frequently missed deadlines.
                    3. Suggestions for improving task completion.
                    """
                    
                    try:
                        # Use OpenAI to generate insights
                        response = llm.predict(prompt)  # Use `predict` instead of calling the object directly
                        
                        # Check if the response is valid
                        if response:
                            st.write("### AI Insights:")
                            st.write(response)  # Directly display the response
                        else:
                            st.error("Invalid response from OpenAI. Please try again.")
                    except Exception as e:
                        st.error(f"Error generating insights: {str(e)}")
            else:
                st.warning("No task or time tracking data available for insights.")

    # Logout Button
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['points'] = 0
        st.success("Logged out successfully!")
        st.rerun()

# Close DB connection
conn.close()