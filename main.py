from datetime import datetime
import uuid

from bedrock_agent_helper import BedrockAgent
from function_calls import get_bedrock_tools, convert_tools_to_function_schema
from location_tools import search_near

# Example usage:
if __name__ == "__main__":
    # Get the bedrock tools and convert to function schema
    tools = get_bedrock_tools()
    function_schema = convert_tools_to_function_schema(tools)

    # Initialize the agent
    agent = BedrockAgent(
        session_id=str(uuid.uuid4()),
        model_id="us.amazon.nova-pro-v1:0",
        action_groups=[{
            'actionGroupName': 'LocationActions',
            'actionGroupExecutor': {'customControl': 'RETURN_CONTROL'},
            'description': 'Tool for retrieving location.',
            'functionSchema': function_schema
        }],
        instructions="""
            You are a helpful location aware agent.
            You search for things to do based on the context provided through the input.  
            Always Use the tools provided along with the context to provide the best answers to the human's questions.
        """
    )

    # Set up session attributes
    session_attributes = {
        'current_date': datetime.now().strftime("%m/%d/%Y"),
        'latitude': '38.689949',
        'longitude': '-28.214581',
        'radius': '100',
    }

    while True:
        command = input("Enter a command (or 'quit' to exit): ")
        if command.lower() == 'quit':
            break
        # Make a query
        response = agent.invoke_agent(
            command,
            session_attributes
        )
        print(response)