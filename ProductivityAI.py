

import openai
import json
import os
from datetime import datetime
import streamlit as st
from typing import List
from dataclasses import dataclass, asdict
import streamlit_calendar as calendar
from typing import Dict
from datetime import datetime,timedelta
from dotenv import load_dotenv

st.set_page_config(page_title="AI Productivity Assistant", layout="wide")

st.markdown("""
    <style>
    /* Global App Background and Font */
    body, .stApp {
        background-color: #ffffff;
        color: #003366;
        font-family: 'Segoe UI', sans-serif;
    }

    /* Sidebar */
    .css-1d391kg {  /* Sidebar header */
        background-color: #e6f0ff !important;
        color: #003366 !important;
    }

    /* Task blocks */
    .task-block {
        background-color: #f0f8ff;
        border-left: 4px solid #0077cc;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 10px;
    }

    /* Completed task style */
    .completed-task {
        opacity: 0.75;
        padding: 10px;
        border-left: 4px solid #009688;
        background-color: #e0f7fa;
        margin: 5px 0;
        border-radius: 4px;
    }

    /* Buttons and Sliders */
    .stButton>button {
        background-color: #0077cc;
        color: white;
        border-radius: 6px;
    }
    .stButton>button:hover {
        background-color: #005fa3;
    }
       /* Sidebar Header */
    .css-1d391kg {
        color: white !important;
    }       
            

    /* Expander Header */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #005fa3;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background-color: #e6f0ff;
        color: #003366;
    }
            

    /* Markdown Headers */
    h1, h2, h3 {
        color: #005fa3;
    }
    </style>
""", unsafe_allow_html=True)







load_dotenv()  # Load .env file
openai.api_key = os.getenv("OPENAI_API_KEY")

@dataclass
class Task:
    name: str
    due_date: str
    estimated_duration: float
    priority: str
    category: str
    status: str = "pending"

    def __post_init__(self):
        if isinstance(self.due_date, str):
            self.due_date = datetime.fromisoformat(self.due_date).date().isoformat()

class ProductivityAssistant:
    def __init__(self, save_file="tasks_data.json"):
        self.tasks: List[Task] = []
        self.schedule = {}
        self.save_file = save_file
        self.load_data()

    def add_task(self, task: Task):
        if self._validate_task(task):
            self.tasks.append(task)
            self._prioritize_tasks()
            self.save_data()
            return True
        return False

    def _validate_task(self, task: Task) -> bool:
        if not task.name.strip():
            st.error("Task name cannot be empty")
            return False
        try:
            datetime.fromisoformat(task.due_date)
        except ValueError:
            st.error("Invalid due date format")
            return False
        return True

    def _prioritize_tasks(self):
        try:
            prompt = f"""Prioritize these tasks considering due dates, durations, and categories:
            {[asdict(task) for task in self.tasks]}
            Return JSON with keys: high, medium, low containing task name arrays."""

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            response_content = response.choices[0].message.content
            priorities = json.loads(response_content)

            for task in self.tasks:
                task.priority = (
                    'high' if task.name in priorities.get('high', []) else
                    'medium' if task.name in priorities.get('medium', []) else 'low'
                )
            st.success("Tasks prioritized!")
        except Exception as e:
            st.error(f"Prioritization error: {str(e)}")

    def save_data(self):
        try:
            with open(self.save_file, "w") as f:
                json.dump({
                    "tasks": [asdict(t) for t in self.tasks],
                    "schedule": self.schedule
                }, f, indent=4)
        except Exception as e:
            st.error(f"Save error: {str(e)}")

    def load_data(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r") as f:
                    data = json.load(f)
                    self.tasks = [Task(**t) for t in data.get("tasks", [])]
                    self.schedule = data.get("schedule", {})
            except Exception as e:
                st.error(f"Load error: {str(e)}")


    def generate_study_schedule(self, available_hours: int, days: int) -> Dict[str, list]:
        """Generate time-block-based schedule"""
        try:
            # Set the starting date
            start_date = datetime.now()  # or you can use a specific date like datetime(2025, 2, 23)
            
            # Construct the prompt with a dynamic start date
            prompt = f"""Create a time-block schedule for these tasks:
            {[asdict(t) for t in self.tasks if t.status == "pending"]}
            Each task should be distributed evenly over the {days} days, considering the {available_hours} available hours per day.
            Ensure no task is repeated on the same day unless necessary, and the total time does not exceed the available hours per day.
            Start each day at 08:00 AM
            
            Start date: {start_date.strftime('%Y-%m-%d')}
            
            Return JSON format:
            {{
                "YYYY-MM-DD": [
                    {{"time": "HH:MM-HH:MM", "task": "Name", "duration": X.X}},
                    ...
                ]
            }}
            """
            
            # Make the OpenAI API request
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            # Parse the response and handle errors
            response_content = response.choices[0].message.content
            print("🔹 OpenAI Response:", response_content)  # ✅ Add this line for debugging
            
            self.schedule = json.loads(response_content)

            # Adjust dates dynamically
            final_schedule = {}
            for i, (date_str, tasks) in enumerate(self.schedule.items()):
                current_date = start_date + timedelta(days=i)
                formatted_date = current_date.strftime('%Y-%m-%d')
                final_schedule[formatted_date] = tasks

            self.schedule = final_schedule
            self.save_data()
            return self.schedule
        except json.JSONDecodeError:
            st.error("Failed to parse schedule response from OpenAI. Response was not valid JSON.")
        except Exception as e:
            st.error(f"Scheduling error: {str(e)}")
        return {}

def main():
    # Ensure session state initializes ProductivityAssistant before accessing it
    if 'assistant' not in st.session_state:
        st.session_state.assistant = ProductivityAssistant()  # Initialize it here

    st.title("🎓 AI Productivity Assistant")
    st.markdown("""
    <style>
    .white-label {
        color: white !important;
    }
                
    <style>
    /* Force the "Add Task" button text to be white */
    button[kind="formSubmit"] {
        color: white !important;
    }
    .st-emotion-cache-1n76uvr { /* Sidebar header class */
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)



    if not hasattr(st.session_state, "assistant"):
        st.error("Assistant not initialized. Please restart the app.")
        return  # Prevent further execution if assistant is missing
    
    # Sidebar - Task Creation
    with st.sidebar:
        
        with st.sidebar:
            st.markdown('<h2 class="white-label">➕ New Task</h2>', unsafe_allow_html=True)
            with st.form("task_form", clear_on_submit=True):
                name = st.text_input("Task Name")
                due_date = st.date_input("Due Date")
                duration = st.number_input("Hours Needed", min_value=0.5, step=0.5)
                category = st.selectbox("Category", ["Study", "Work", "Personal"])
                submitted = st.form_submit_button("Add Task")
                    
            if submitted:
                new_task = Task(
                    name=name.strip(),
                    due_date=due_date.isoformat(),
                    estimated_duration=duration,
                    priority="medium",
                    category=category
                )
                st.session_state.assistant.add_task(new_task)
                st.toast(f"Added: {name}", icon="✅")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("📅 Daily Tasks")
        selected_date = st.date_input("Select Date")
        date_tasks = [
            t for t in st.session_state.assistant.tasks
            if t.due_date == selected_date.isoformat()
        ]
        
        if date_tasks:
            for task in date_tasks:
                with st.expander(f"{task.name} ({task.priority.upper()})"):
                    st.markdown(f"""
                    - 📅 Due: {task.due_date}
                    - ⏳ Duration: {task.estimated_duration}h
                    - 🏷️ Category: {task.category}
                    - 🚦 Status: {task.status}
                    """)
        else:
            st.markdown("""
<div style="background-color:#e7f3fe; color:black; padding:10px; border-left:6px solid #2196F3; border-radius:5px;">
    ℹ️ No tasks for this date
</div>
""", unsafe_allow_html=True)


    with col2:
        st.header("📝 Task Management")
        tab1, tab2 = st.tabs(["Pending", "Completed"])

        with tab1:
            pending = [t for t in st.session_state.assistant.tasks if t.status == "pending"]
            if pending:
                for task in sorted(pending, key=lambda x: x.priority):
                    with st.expander(f"{task.name} ({task.priority.upper()})"):
                        st.markdown(f"""
                        - 📅 {task.due_date}
                        - ⏳ {task.estimated_duration}h
                        - 🏷️ {task.category}
                        """)
                        if st.button("✔ Complete", key=f"complete_{task.name}"):
                            task.status = "resolved"
                            st.session_state.assistant.save_data()
                            st.rerun()
            else:
                
                st.markdown("""
<div style="background-color:#e7f3fe; color:black; padding:10px; border-left:6px solid #2196F3; border-radius:5px;">
    All tasks completed! 🎉
</div>
""", unsafe_allow_html=True)


        with tab2:
            completed = [t for t in st.session_state.assistant.tasks if t.status == "resolved"]
            if completed:
                for task in completed:
                    st.markdown(f"""
                    <div style="opacity:0.7; padding:10px; border-left:3px solid #4CAF50; margin:5px 0;">
                        ~~{task.name}~~<br>
                        <small>Completed on {datetime.now().date().isoformat()}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No completed tasks yet")

    # Schedule Generator
st.header("⏳ Schedule Generator")


if __name__ == "__main__":
    main()

