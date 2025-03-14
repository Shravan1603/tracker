import streamlit as st
from langchain.chat_models import ChatOpenAI
import db
import os
from dotenv import load_dotenv
import re

# Load environment variables (e.g., OpenAI API key)
load_dotenv()
conn = db.init_db()

# Initialize OpenAI
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=os.getenv("OPENAI_API_KEY"))

# Fetch completed tasks from the database
def fetch_completed_tasks():
    tasks = conn.execute("""
        SELECT topic, subtopics, category 
        FROM tasks 
        WHERE status = 'Completed'
    """).fetchall()
    return tasks

# Generate quiz questions using OpenAI
def generate_quiz(topic, subtopics, num_questions=5):
    prompt = f"""
    Generate {num_questions} quiz questions based on the following completed task:
    Topic: {topic}
    Subtasks: {subtopics if subtopics else "None"}

    Include a mix of multiple-choice and open-ended questions.
    Format the output as follows:
    1. Question: What is a variable in Python?
       Type: multiple-choice
       Options: A) A container for storing data, B) A function, C) A loop
       Answer: A
    2. Question: What is a loop in Python?
       Type: open-ended
       Answer: A loop is used to repeat a block of code.
    """
    response = llm.invoke(prompt)
    return response.content

# Parse the quiz content into a structured format
def parse_quiz(quiz_content):
    """Parse the raw quiz content into a structured list of questions."""
    questions = []
    current_question = None

    # Regex patterns for different parts
    question_pattern = re.compile(r"^\d+\.\s*Question:(.+)")
    type_pattern = re.compile(r"^\s*Type:\s*(.+)")
    options_pattern = re.compile(r"^\s*Options:\s*(.+)")
    answer_pattern = re.compile(r"^\s*Answer:\s*(.+)")

    for line in quiz_content.split('\n'):
        line = line.strip()

        # Start a new question
        if match := question_pattern.match(line):
            if current_question:
                questions.append(current_question)
            current_question = {
                "question": match.group(1).strip(),
                "type": None,
                "options": [],
                "answer": None
            }

        # Capture the type
        elif match := type_pattern.match(line):
            if current_question:
                current_question["type"] = match.group(1).strip()

        # Capture options (handles embedded commas correctly)
        elif match := options_pattern.match(line):
            if current_question:
                raw_options = match.group(1).strip()
                current_question["options"] = re.findall(r"[A-C]\) [^A-C]+?(?=(, [A-C]\)|$))", raw_options)

        # Capture the answer
        elif match := answer_pattern.match(line):
            if current_question:
                current_question["answer"] = match.group(1).strip()

    # Add the last question
    if current_question:
        questions.append(current_question)

    return questions


# Evaluate user answers and provide feedback
def evaluate_answers(questions, user_answers):
    feedback = []
    score = 0
    
    for i, (question, user_answer) in enumerate(zip(questions, user_answers)):
        if question["type"] == "multiple-choice":
            if user_answer == question["answer"]:
                feedback.append(f"✅ **Question {i+1}:** Correct!")
                score += 1
            else:
                feedback.append(
                    f"❌ **Question {i+1}:** Incorrect.\n\n"
                    f"Your answer: {user_answer}\n\n"
                    f"Correct answer: **{question['answer']}**\n\n"
                    f"Explanation: {question.get('explanation', 'No explanation provided.')}"
                )
        elif question["type"] == "open-ended":
            feedback.append(
                f"💡 **Question {i+1}:**\n\n"
                f"Your answer: {user_answer}\n\n"
                f"Correct answer: **{question['answer']}**\n\n"
                f"Explanation: {question.get('explanation', 'No explanation provided.')}"
            )
            score += 1

    
    # Add a progress bar for the score
    st.progress(score / len(questions))
    
    # Display the score breakdown
    st.markdown(f"### 🏁 Your Final Score: **{score}/{len(questions)}**")
    
    # Display detailed feedback for each question
    st.markdown("### 📝 Feedback")
    for fb in feedback:
        st.markdown(fb)
    
    # Additional motivational message based on the score
    if score == len(questions):
        st.balloons()
        st.success("🎉 Perfect score! Well done!")
    elif score >= len(questions) / 2:
        st.success("👍 Good job! Keep it up!")
    else:
        st.warning("💪 Keep practicing! You're getting better!")

    return None  # No need to return feedback as it's displayed directly

# Main function
def ai_quiz_generation():
    st.title("🧠 AI-Powered Quiz Generator")
    st.write("Generate quizzes from your completed tasks!")

    # Fetch completed tasks
    tasks = fetch_completed_tasks()

    if tasks:
        # Let the user select a task
        selected_task = st.selectbox("✅ Select a completed task to generate a quiz", [task[0] for task in tasks])
        subtopics = next(task[1] for task in tasks if task[0] == selected_task)

        # Let the user specify the number of questions
        num_questions = st.number_input("🎯 Number of questions", min_value=1, max_value=10, value=5)

        # Generate quiz
        if st.button("🚀 Generate Quiz"):
            try:
                quiz_content = generate_quiz(selected_task, subtopics, num_questions)
                st.session_state['quiz'] = parse_quiz(quiz_content)
                st.session_state['user_answers'] = [""] * len(st.session_state['quiz'])
                st.session_state['feedback'] = None
                st.success("✅ Quiz generated successfully!")
            except Exception as e:
                st.error(f"⚠️ Failed to generate quiz: {str(e)}")

        # Display quiz and collect answers
        if 'quiz' in st.session_state:
            st.write("### ✨ Quiz Time!")
            for i, question in enumerate(st.session_state['quiz']):
                if "question" in question and question["question"]:
                    st.write(f"**📝 Question {i+1}:** {question['question']}")

                    if question["type"] == "multiple-choice" and question["options"]:
                        user_answer = st.radio(
                            f"🔍 Select an answer for question {i+1}",
                            question["options"],
                            key=f"answer_{i}"
                        )
                    else:
                        user_answer = st.text_input(
                            f"✏️ Your answer for question {i+1}", key=f"answer_{i}"
                        )

                    st.session_state['user_answers'][i] = user_answer

                else:
                    st.error(f"⚠️ Invalid question format: {question}")

            if st.button("✅ Submit Quiz"):
                try:
                    feedback = evaluate_answers(st.session_state['quiz'], st.session_state['user_answers'])
                    st.session_state['feedback'] = feedback
                    st.success("🏁 Quiz submitted successfully!")
                except Exception as e:
                    st.error(f"⚠️ Failed to evaluate answers: {str(e)}")

            # Display feedback
            if 'feedback' in st.session_state and st.session_state['feedback']:
                st.write("### 📊 Quiz Feedback")
                st.write(st.session_state['feedback'])

    else:
        st.warning("⚠️ No completed tasks available for quiz generation.")

# Add this to your panel options
if __name__ == "__main__":
    ai_quiz_generation()
