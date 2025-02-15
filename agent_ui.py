import folium
import json
import re
import streamlit as st
import uuid
from enum import Enum
from streamlit_folium import folium_static

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

def parse_json_message(message):
    try:
        data = json.loads(message)
        text = data.get("text", message)
        locations = data.get("locations", None)
    except (json.JSONDecodeError, TypeError):
        text = message
        locations = None
    return text, locations

def parse_tagged_message(message):
    pattern = re.compile(r'<place id="(?P<id>[^"]+)" lat=(?P<lat>[^ ]+) lng=(?P<lng>[^ ]+)>(?P<name>[^<]+)</place>')

    locations = []
    def replace_tag(match):
        location = {
            'id': match.group('id'),
            'lat': float(match.group('lat')),
            'lng': float(match.group('lng')),
            'name': match.group('name')
        }
        locations.append(location)
        return f'<a href="https://foursquare.com/v/{location["id"]}" target="_blank" rel="noreferrer nofollow noopener">{location["name"]}</a>'

    # Replace the tags in the message and collect location data
    text = pattern.sub(replace_tag, message)

    return text, locations

def create_map(locations):
    m = folium.Map()
    for location in locations:
        folium.Marker(
            [location['lat'], location['lng']],
            icon=folium.DivIcon(
                html=f"""
                <div style="white-space: nowrap; font-size: 14px; color: black; font-weight: bold; text-shadow: 1px 0 white, -1px 0 white, 0 1px white, 0 -1px white;">
                  <img src="https://ss0.4sqi.net/img/leaflet/images/marker-icon-ed9aa0b76a58a5a016efad37b874348e.png" style="vertical-align: middle; width: 16px; height: 24px;">
                  {location['name']}
                </div>"""
            )
        ).add_to(m)
    bounds = [[location['lat'], location['lng']] for location in locations]
    m.fit_bounds(bounds)
    return m

def generate_response_from_agent(input_text: str, final_text_placeholder, map_placeholder):
    completion_event = None

    for event in agent.invoke_agent(input_text, session_attributes=session_attributes):
        if event.type != EventType.COMPLETION:
            yield event
        else:
            completion_event = event

    text, locations = parse_tagged_message(completion_event.data)

    with final_text_placeholder:
        with st.container(border=True):
            scrolling_html = f"""
            <div style="max-height: 200px; overflow: auto;">
                {text}
            </div>
            """
            st.components.v1.html(scrolling_html, height=200)

    if locations:
        map_object = create_map(locations)
        with map_placeholder:
            folium_static(map_object, width=500, height=300)
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
        map_placeholder = st.empty()
        human_placeholder.container(border=True).chat_message(name="human").write(prompt)
        status_bar = st.status("Invoking agent...", expanded=True)
        response_container = st.empty()
        # Stream the response
        responses = []
        for event in generate_response_from_agent(prompt, final_text_placeholder, map_placeholder):
            responses.append(event)
            response_container.container().empty()
            with response_container.container(border=True, height=600):
                for response in reversed(responses):
                    st.write(response)
        status_bar.update(label="Final Answer!", state="complete", expanded=False)

