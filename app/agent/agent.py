from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from app.agent.config import LLM_CONFIG
from typing import Dict

search_agent = AssistantAgent(
    name="search_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "search for information about user provided topic"
    ),
)

visual_agent = AssistantAgent(
    name="search_agent",
    llm_config=LLM_CONFIG,
    system_message=(
        "make a chart based on the data from search_agent"
    ),
)

internal_critic = AssistantAgent(
    name="internal_critic",
    llm_config=LLM_CONFIG,
    system_message=(
        "check if the chart matches the expected output"
    ),
)

user_proxy = UserProxyAgent(
    name="user_proxy",
    llm_config=False,
    human_input_mode="NEVER",
    is_termination_msg=lambda m: "TERMINATE" in m.get("content", ""),
    code_execution_config=False,
)

def make_groupchat() -> GroupChatManager:
    group = GroupChat(
        agents=[user_proxy, search_agent, internal_critic],  # FIXED
        messages=[],
        max_round=25,
        speaker_selection_method="auto",
    )
    return GroupChatManager(groupchat=group, llm_config=LLM_CONFIG)

def run_with_internal_critic(user_request: str) -> Dict:
    manager = make_groupchat()
    init_message = user_request 

    try:
        final = user_proxy.initiate_chat(manager, message=init_message)
        trace = list(manager.groupchat.messages)
    except Exception as e:
        print(f"Chat error: {e}")
        trace = list(manager.groupchat.messages) if hasattr(manager, "groupchat") else []
        final = None

    return {"final": final, "trace": trace} 


if __name__ == "__main__":
    print("Research Agent Evaluation WITH GroupChat + Internal Critic\n")
    result = run_with_internal_critic("show me the wage increase for danes from 2020-2025")  # ADDED
    print(result)
