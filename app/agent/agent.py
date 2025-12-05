# agent.py
import os
import json
import pandas as pd
from app.agent.config import LLM_CONFIG
from typing import Dict
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from app.tools.chart_tool import create_chart

# Optional: yfinance for stock data (no API key required)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception:
    YFINANCE_AVAILABLE = False

# ----------------------------
# Tools
# ----------------------------

def load_csv(filename: str) -> str:
    """
    Load CSV from input/filename and return JSON describing columns and data.
    """
    try:
        input_path = os.path.join("input", filename)
        if not os.path.exists(input_path):
            return json.dumps({"error": f"File '{filename}' not found in input/ folder."})

        df = pd.read_csv(input_path)
        return json.dumps({
            "source": "csv",
            "filename": filename,
            "columns": list(df.columns),
            "data": df.to_dict(orient="list")
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def fetch_stock(ticker: str, start: str = None, end: str = None) -> str:
    """
    Download historical stock data using yfinance and return JSON.
    start/end are 'YYYY-MM-DD' strings (optional).
    """
    if not YFINANCE_AVAILABLE:
        return json.dumps({"error": "yfinance not installed or failed to import."})
    try:
        # yfinance .download returns a DataFrame with DatetimeIndex
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
        if df.empty:
            return json.dumps({"error": f"No data returned for ticker {ticker}."})
        if isinstance(df.columns, pd.MultiIndex):
                # We take the last level, which usually contains the column name (Open, Close, etc.)
                df.columns = df.columns.get_level_values(-1)
            # 2. Rename columns to ensure they are clean strings for the chart agent
        df.columns = [col.replace(' ', '_') for col in df.columns]# Keep the index as a 'date' column
        df = df.reset_index()
        # Convert Timestamp to string for JSON serialization
        df['Date'] = df['Date'].dt.strftime("%Y-%m-%d")
        return json.dumps({
            "source": "yfinance",
            "ticker": ticker,
            "columns": list(df.columns),
            "data": df.to_dict(orient="list")
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

# ----------------------------
# Agents
# ----------------------------

data_agent = AssistantAgent(
    name="data_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "You are a Data Loader agent.\n"
        "User will ask to visualize data either by providing a filename (CSV in /input/)\n"
        "or by requesting a stock ticker (e.g., 'META' with start & end dates).\n\n"
        "You must:\n"
        "1) Determine whether the user request is for a CSV file or a stock ticker.\n"
        "   - If CSV: call load_csv(filename)\n"
        "   - If stock ticker: call fetch_stock(ticker, start, end)\n"
        "2) Return the JSON result from the tool so the visual_agent can decide how to plot.\n\n"
        "Examples of user requests:\n"
        "- 'Visualize the file wages_2020_2025.csv: plot year vs wage_index'\n"
        "- 'Show a line chart of META adjusted close from 2023-01-01 to 2023-01-31'\n\n"
        "If file/ticker not found, return an informative error message."
    )
)

visual_agent = AssistantAgent(
    name="visual_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "You are a Visualization agent.\n"
        "You will receive JSON (columns and data) from data_agent.\n"
        "Your job:\n"
        "1) Decide which columns correspond to x (e.g., Date, year) and y (e.g., Adj Close, wage_index).\n"
        "2) Choose an appropriate chart type (line for time series).\n"
        "3) Prepare the create_chart call with JSON data in the form:\n"
        '   {"x_values": [...], "y_values": [...], "labels": [...]}\n'
        "4) Call create_chart(chart_type, data_json_str, title, x_label, y_label, filename)\n\n"
        "Do NOT invent values; only use the data provided."
    )
)

critic_agent = AssistantAgent(
    name="critic_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "You are a critic. Evaluate the chart creation response.\n"
        "If the chart was created successfully, reply:\n"
        "\"APPROVED: Chart created successfully. TERMINATE\"\n"
        "If there's an error or mismatch, give actionable feedback for visual_agent."
    )
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    llm_config=False,
    human_input_mode="NEVER",
    code_execution_config=False,
    is_termination_msg=lambda m: "TERMINATE" in m.get("content", "")
)

# register tools for LLMs
data_agent.register_for_llm(name="load_csv", description="Load a CSV file from input/")(load_csv)
data_agent.register_for_llm(name="fetch_stock", description="Fetch historical stock data via yfinance")(fetch_stock)

visual_agent.register_for_llm(name="create_chart", description="Create a chart from data")(create_chart)

# user_proxy executes tools
user_proxy.register_for_execution(name="load_csv")(load_csv)
user_proxy.register_for_execution(name="fetch_stock")(fetch_stock)
user_proxy.register_for_execution(name="create_chart")(create_chart)

# ----------------------------
# Group chat flow control
# ----------------------------

def custom_speaker_selection(last_speaker, groupchat):
    msgs = groupchat.messages
    if len(msgs) <= 1:
        return data_agent

    last = msgs[-1]
    last_name = last.get("name", "")
    content = last.get("content", "")

    # After data_agent returns data, go to visual_agent
    if last_name == "data_agent":
        if "error" in content.lower():
            # If error, end (user must fix) or stay on data_agent
            return data_agent
        return user_proxy

    # After visual agent, go to critic
    if last_name == "visual_agent":
        return critic_agent

    # After critic approves, end
    if last_name == "critic_agent":
        if "APPROVED" in content.upper():
            return None
        return visual_agent

    return data_agent

def make_groupchat():
    return GroupChatManager(
        groupchat=GroupChat(
            agents=[user_proxy, data_agent, visual_agent, critic_agent],
            messages=[],
            speaker_selection_method="auto",
            max_round=12,
        ),
        llm_config=LLM_CONFIG
    )

def run(user_request: str):
    """
    Entrypoint to run the groupchat with a user request.
    Example user_request:
      'Show a line chart of the adjusted closing price of META from 2023-01-01 to 2023-01-31.'
      'Visualize the file wages_2020_2025.csv: year vs wage_index'
    """
    manager = make_groupchat()
    final = user_proxy.initiate_chat(manager, message=user_request)
    return final

if __name__ == "__main__":
    # demo prompt (assignment example)
    prompt = "Show a line chart of the adjusted closing price of META from 2023-01-01 to 2023-01-31."
    print("Running demo prompt:\n", prompt)
    result = run(prompt)
    print("Final result:\n", result)
