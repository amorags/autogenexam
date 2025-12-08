# agent.py
from app.agent.config import LLM_CONFIG
from typing import Dict
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from app.tools.load_tool import load_csv
from app.tools.fetch_tool import fetch_stock
from app.tools.chart_tool import create_chart

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
        "2) After calling the tool, wait for user_proxy to execute it.\n"
        "3) Once you receive the JSON result, pass it to visual_agent.\n\n"
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
        "1) Parse the JSON to extract columns and data.\n"
        "2) Decide which columns correspond to x (e.g., Date, year) and y (e.g., Adj Close, wage_index).\n"
        "3) Choose an appropriate chart type (line for time series).\n"
        "4) Extract the actual data values from the JSON.\n"
        "5) Call create_chart with properly formatted JSON data:\n"
        '   {"x_values": [actual values], "y_values": [actual values], "labels": []}\n'
        "6) Wait for user_proxy to execute the chart creation.\n\n"
        "IMPORTANT: Use the actual data values from the JSON, do NOT use empty arrays.\n"
        "Do NOT invent values; only use the data provided."
    )
)

critic_agent = AssistantAgent(
    name="critic_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "You are a critic. Evaluate the chart creation response from user_proxy.\n"
        "Look for the JSON response that indicates success or failure.\n"
        "If the chart was created successfully (look for 'status: success'), reply:\n"
        "\"APPROVED: Chart created successfully. Proceeding to judge.\"\n"
        "If there's an error or the response indicates failure, give actionable feedback for visual_agent."
    )
)

judge_agent = AssistantAgent(
    name="judge_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "You are a Judge agent that evaluates the overall quality of the chart creation process.\n"
        "Review the entire conversation and assess:\n"
        "1) Data Loading: Was the correct data loaded successfully?\n"
        "2) Visualization: Was an appropriate chart type chosen?\n"
        "3) Accuracy: Do the chart parameters match the user's request?\n"
        "4) Output Quality: Was the chart created without errors?\n\n"
        "Provide a score from 1-10 and detailed feedback:\n"
        "- Score 8-10: Excellent - all requirements met perfectly\n"
        "- Score 5-7: Good - minor issues or improvements possible\n"
        "- Score 1-4: Poor - significant issues or errors\n\n"
        "Format your response as:\n"
        "SCORE: X/10\n"
        "FEEDBACK: [Your detailed analysis]\n"
        "TERMINATE"
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
    """
    Robust speaker selection based on agent identity rather than message content.
    """
    msgs = groupchat.messages
    
    # 1. Start with data_agent
    if len(msgs) <= 1:
        return data_agent

    last_msg = msgs[-1]
    last_name = last_msg.get("name", "")
    
    # 2. If the last message was a tool execution by user_proxy:
    if last_name == "user_proxy":
        # Look at the message immediately before the user_proxy (the tool caller)
        if len(msgs) >= 2:
            tool_caller = msgs[-2].get("name", "")
            
            # If Data Agent called the tool -> Pass result to Visual Agent
            if tool_caller == "data_agent":
                return visual_agent
            
            # If Visual Agent called the tool -> Pass result to Critic
            if tool_caller == "visual_agent":
                return critic_agent
                
    # 3. If Data Agent just spoke:
    if last_name == "data_agent":
        # If it's a tool call, go to user_proxy
        if "tool_calls" in last_msg or "Suggested tool call" in last_msg.get("content", ""):
            return user_proxy
        # If it has data/columns (text response), hand off to visual_agent
        if "columns" in last_msg.get("content", ""):
            return visual_agent
        # Error or other, stay on data_agent (or handle error)
        return data_agent

    # 4. If Visual Agent just spoke:
    if last_name == "visual_agent":
        # If it's a tool call, execute it
        if "tool_calls" in last_msg or "Suggested tool call" in last_msg.get("content", ""):
            return user_proxy
        # Otherwise, keep trying
        return visual_agent

    # 5. Critic Flow
    if last_name == "critic_agent":
        content = last_msg.get("content", "").upper()
        if "APPROVED" in content:
            return judge_agent
        # If rejected, send back to visual_agent to fix
        return visual_agent

    # 6. Judge Flow
    if last_name == "judge_agent":
        # Terminate or loop done
        return None

    # Default fallback (usually starts the conversation)
    return data_agent

def make_groupchat():
    return GroupChatManager(
        groupchat=GroupChat(
            agents=[user_proxy, data_agent, visual_agent, critic_agent, judge_agent],
            messages=[],
            speaker_selection_method=custom_speaker_selection,
            max_round=20,
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
    print("=" * 60)
    print("AutoGen Chart Generation System")
    print("=" * 60)
    print("\nExamples of requests you can make:")
    print("1. 'Show a line chart of the adjusted closing price of AAPL from 2023-01-01 to 2023-01-31'")
    print("2. 'Visualize the file wages_2020_2025.csv: plot year vs wage_index'")
    print("3. 'Create a bar chart of META stock volume from 2023-01-01 to 2023-03-01'")
    print("\nType 'quit' or 'exit' to stop.\n")
    
    while True:
        user_input = input("Enter your request: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not user_input:
            print("Please enter a valid request.\n")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing: {user_input}")
        print(f"{'='*60}\n")
        
        try:
            result = run(user_input)
            print("\n" + "="*60)
            print("Request completed!")
            print("="*60 + "\n")
        except Exception as e:
            print(f"\nError: {str(e)}\n")
            print("Please try again with a different request.\n")