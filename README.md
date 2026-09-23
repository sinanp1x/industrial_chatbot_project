# Chatbot - Industrial Copilot & Equipment Diagnostics

![Chatbot](https://img.shields.io/badge/Chatbot-Industrial_Copilot-blue)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](Chatbot_Colab.ipynb)

Chatbot bridges the gap between static industrial documentation (machinery operating manuals, SOPs, safety guides) and dynamic telemetry (PLC event logs, sensor dumps, error logs).

It uses **Hugging Face** to provide powerful, grounded answers from your manuals and logs.

## 🚀 Running in Google Colab (Recommended)

You can easily run this entire system for free in a Google Colab notebook, using Colab's hardware and directly exposing the Streamlit app.

### Option 1: Use the Provided Notebook
1. Upload `Chatbot_Colab.ipynb` to your Google Drive and open it with Google Colab.
2. Run the cells in order.
3. The notebook will use `localtunnel` to provide a public URL to your running Streamlit app. You will need to enter the "Endpoint IP" into the localtunnel warning page (the notebook provides instructions on how to get it).
4. Enter your Hugging Face API Token in the app sidebar to start chatting.

### Option 2: Manual Colab Setup
Create a new Colab notebook and run the following commands in a cell:

```bash
# 1. Clone the repository
!git clone https://github.com/YOUR_GITHUB_USERNAME/industrial_chatbot_project.git
%cd industrial_chatbot_project

# 2. Install dependencies
!pip install -r requirements.txt
!pip install localtunnel

# 3. Run Streamlit in the background
!streamlit run app.py &>/content/logs.txt &

# 4. Expose the port using localtunnel
!npx localtunnel --port 8501
```

## 💻 Running Locally

If you prefer to run it on your own machine:

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Hugging Face API token in a `.env` file or directly in the UI:
   ```
   HUGGINGFACEHUB_API_TOKEN="your_token_here"
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## 📚 Documentation
Check the `docs/` folder for comprehensive documentation on the architecture, RAG pipelines, LangGraph workflows, and UI specifications.
