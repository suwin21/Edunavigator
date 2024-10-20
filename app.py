import os
from flask import Flask, render_template, request, jsonify
import pandas as pd
from groq import Groq

# Initialize Flask app
app = Flask(__name__)

# Load the CSV into a DataFrame
colleges = pd.read_csv("final.csv")

# Extract dynamic options from the CSV with proper cleaning
def safe_unique_values(column):
    return ['Any'] + sorted(colleges[column].dropna().astype(str).unique().tolist())

features = colleges.columns.tolist()
courses_list = safe_unique_values('Course')
cities_list = safe_unique_values('City')
branches_list = safe_unique_values('Branch')
college_types = safe_unique_values('College Type')

# Generate fee ranges dynamically with custom labels
def create_fee_ranges(data):
    ranges = [
        "Below 50,000",
        "Below 100,000",
        "Below 200,000",
        "Below 300,000",
        "Above 300,000"
    ]
    return ['Any'] + ranges

fee_ranges = create_fee_ranges(colleges['Average Fees'].dropna())

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/apply", methods=["GET", "POST"])
def apply():
    if request.method == "POST":
        # Collect form data
        city = request.form.get("city")
        college_type = request.form.get("college_type")
        fees_range = request.form.get("fees")
        cutoff = float(request.form.get("cutoff"))
        branch = request.form.get("branch")
        selected_courses = request.form.getlist("courses")

        # Parse the selected fees range
        if fees_range == "Any":
            min_fees, max_fees = 0, float('inf')
        elif fees_range.startswith("Below"):
            max_fees = int(fees_range.split()[1].replace(",", ""))
            min_fees = 0
        else:  # For "Above"
            min_fees = int(fees_range.split()[1].replace(",", ""))
            max_fees = float('inf')

        # Filter DataFrame based on user input
        filtered_colleges = colleges[
            ((colleges["City"] == city) | (city == 'Any')) &
            ((colleges["College Type"] == college_type) | (college_type == 'Any')) &
            ((colleges["Average Fees"] >= min_fees) & (colleges["Average Fees"] <= max_fees)) &
            (colleges["cutoff"] <= cutoff) &
            ((colleges["Branch"] == branch) | (branch == 'Any')) &
            ((colleges["Course"].isin(selected_courses)) | ('Any' in selected_courses))
        ]

        # Render template and pass the filtered results and zip function
        return render_template(
            "suggestions.html",
            clg_list=filtered_colleges.values,
            features=features,
            zip=zip  # Pass the zip function to use in the template
        )

    return render_template(
        "apply.html", 
        courses=courses_list, 
        cities=cities_list, 
        branches=branches_list, 
        fees_list=fee_ranges,
        college_types=college_types
    )

@app.route("/suggestions")
def suggestions():
    return render_template("suggestions.html", clg_list=[], features=features)

# Route for FAQs page
@app.route("/faqs")
def faqs():
    return render_template("faqs.html")

# Route for the chatbot page
@app.route("/chat")
def chat():
    return render_template("chat.html")  # Render the chat.html page

# Chatbot functionality
@app.route('/ask', methods=['POST'])
def ask_chatbot():
    user_input = request.form['user_input']
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    # System prompt to act as a TNEA specialist
    system_prompt = """You are an AI assistant specializing in Tamil Nadu Engineering Admissions (TNEA). 
    Your role is to provide accurate and helpful information about the TNEA process, including:
    Your response must be brief and short and crisp,
    You must always provide the following information regarding a college:
    - Eligibility criteria
    - Application procedures
    - Important dates and deadlines
    - Required documents
    - Counselling process
    - Seat allocation
    - Cut-off marks and ranks
    - Popular engineering colleges in Tamil Nadu
    - Various engineering branches and their prospects
    
    Please answer user queries related to TNEA with detailed and up-to-date information. 
    If you're unsure about any specific detail, please inform the user and suggest where they might find the most current information."""

    # Call the Groq API
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_input,
            }
        ],
        model="llama-3.1-70b-versatile",
    )
    
    chatbot_response = response.choices[0].message.content
    return jsonify({'response': chatbot_response})

if __name__ == "__main__":
    app.run(debug=True)
