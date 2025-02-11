import boto3
import json
from typing import Dict, Any, Tuple, Optional

from function_calls import parse_function_parameters, invoke_tool

class BedrockAgent:
    def __init__(
            self,
            session_id: str,
            model_id: str,
            action_groups: list,
            instructions: str,
            region_name: str = "us-west-2"
    ):
        """Initialize the BedrockAgent with required parameters.

        Args:
            session_id: Unique identifier for the session
            model_id: The model identifier to use
            action_groups: List of action groups configuration
            instructions: Agent instructions
            region_name: AWS region name (default: us-west-2)
        """
        self.session_id = session_id
        self.model_id = model_id
        self.action_groups = action_groups
        self.instructions = instructions
        self.invocation_id = None

        # Initialize boto3 client
        session = boto3.Session()
        self.bedrock_rt_client = session.client(
            service_name="bedrock-agent-runtime",
            region_name=region_name
        )

    def _process_response_stream(self, response) -> Tuple[str, bool]:
        """Process the response stream from bedrock agent.

        Args:
            response: The response from invoke_inline_agent

        Returns:
            Tuple containing (output string, boolean indicating if it's a function call)
        """
        output = ""
        is_function_call = False

        for chunk in response['completion']:
            if 'chunk' in chunk:
                output += chunk['chunk']['bytes'].decode('utf-8')
            elif "trace" in chunk:
                print(f"Trace: {chunk['trace']['trace']['orchestrationTrace']}")
            elif 'returnControl' in chunk:
                output = chunk['returnControl']
                is_function_call = True
            else:
                print(chunk)

        return output, is_function_call

    def invoke_agent(
            self,
            input_text: str,
            session_attributes: Dict[str, Any],
            function_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """Invoke the bedrock agent with given input and handle function calls.

        Args:
            input_text: The input text to send to the agent
            session_attributes: Dictionary of session attributes
            function_result: Optional function result from previous invocation

        Returns:
            The agent's response as a string
        """
        # Prepare the session state
        session_state = {
            'promptSessionAttributes': session_attributes,
        }

        # If we have function results from a previous invocation, include them
        if function_result and self.invocation_id:
            session_state.update({
                'invocationId': self.invocation_id,
                'returnControlInvocationResults': [{
                    'functionResult': function_result
                }]
            })

        # Invoke the agent
        response = self.bedrock_rt_client.invoke_inline_agent(
            instruction=self.instructions,
            foundationModel=self.model_id,
            sessionId=self.session_id,
            endSession=False,
            enableTrace=True,
            inputText=input_text,
            inlineSessionState=session_state,
            actionGroups=self.action_groups
        )

        # Process the response
        output, is_function_call = self._process_response_stream(response)

        # If it's a function call, parse and execute it
        if is_function_call:
            function_to_call = parse_function_parameters(output)
            self.invocation_id = function_to_call.get('invocationId')

            if function_to_call['function'] == 'search_near':
                data, error = invoke_tool(function_to_call)

                if error:
                    return f"Error: {error}"

                # Make a second call with the function results
                function_result = {
                    'actionGroup': function_to_call['actionGroup'],
                    'function': function_to_call['function'],
                    'responseBody': {
                        'TEXT': {
                            'body': json.dumps(data, indent=2)
                        }
                    }
                }

                return self.invoke_agent(" ", session_attributes, function_result)

        return output

