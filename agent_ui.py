import streamlit as st
import uuid
from enum import Enum

from bedrock_agent_helper import EventType
from intialize_agent import initialize

from langchain.agents import initialize_agent

agent_session_id = st.session_state.get("agent_session_id", str(uuid.uuid4()))
agent, session_attributes = initialize(agent_session_id)
st.session_state["agent_session_id"] = agent_session_id

st.set_page_config(layout="wide")

class State(str, Enum):
    FINISH = "FINISH"
    ROC = "ROC"

def generate_response_from_agent(input_text: str, final_text_placeholder):
    completion_event = None
    for event in agent.invoke_agent(input_text, session_attributes=session_attributes):
        if event.type != EventType.COMPLETION:
            yield event
        else:
            completion_event = event

    with final_text_placeholder:
        with st.container(border=True):
            with st.chat_message(name="assistant"):
                st.write(f"Assistant: {completion_event.data}")
    return completion_event

# Create two columns
#left_col, right_col = st.columns([2, 1])


# Create a container in the left column for chat
#with left_col:
with st.container(border=True):
    prompt = st.chat_input("Say something")
    if prompt:
        # Create an empty container in the right column for the image
#        with right_col:
        human_placeholder = st.empty()
        image_placeholder = st.empty()
        final_text_placeholder = st.empty()
        human_placeholder.container(border=True).chat_message(name="human").write(prompt)
        status_bar = st.status("Invoking agent...", expanded=True)
        response_container = st.empty()
        # Stream the response
        responses = []
        for event in generate_response_from_agent(prompt, final_text_placeholder):
            responses.append(event)
            response_container.container().empty()
            with response_container.container(border=True, height=600):
                for response in reversed(responses):
                    st.write(response)
        status_bar.update(label="Final Answer!", state="complete", expanded=False)

