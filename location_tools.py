# Constants
import os
from urllib.parse import urlencode
import httpx
from function_calls import bedrock_agent_tool, get_bedrock_tools
import json

FSQ_UNVERSIONED_API_BASE = "https://api.foursquare.com"
FSQ_V20241206_API_BASE = "https://places-api.foursquare.com"

FSQ_SERVICE_TOKEN = os.getenv("FOURSQUARE_SERVICE_TOKEN")

def submit_request(endpoint: str, params: dict[str, str], version20241206: bool) -> str:
    headers = {
        "Authorization": f"Bearer {FSQ_SERVICE_TOKEN}",
    }
    if version20241206:
        headers["X-Places-Api-Version"] = "2024-12-06"
    encoded_params = urlencode(params)
    url_base = FSQ_V20241206_API_BASE if version20241206 else FSQ_UNVERSIONED_API_BASE
    url = f"{url_base}{endpoint}?{encoded_params}"
    with httpx.Client() as client:
        try:
            print(url)
            response = client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text, None
        except Exception as e:
            return "null", str(e)
            #return "Lake Washington Park; Summit at Snoqualmie Skiing; Rocket Bowling", None

@bedrock_agent_tool
def search_near(what: str, where: str=None, lat_long: str=None, radius: int=0) -> str:
    """Search for places near a particular named region or point. Either the
    region must be specified with the near parameter, or a circle around a point
    must be specified with the ll and radius parameters.

    Args:
        what: concept you are looking for (e.g., coffee shop, Hard Rock Cafe)
        where: a geographic region (e.g., Los Angeles or Fort Greene)
        lat_long: latitude and longitude as a comma separated string
        radius: distance in meters
    """
    params = {
        "query": what,
        "limit": 5
    }
    if where:
        params["near"] = where
    elif lat_long and radius:
        params["ll"] = lat_long
        params["radius"] = radius
    return submit_request("/places/search", params, version20241206=True)


if __name__ == "__main__":
    my_bedrock_tools = get_bedrock_tools(False)
    print(json.dumps(my_bedrock_tools, indent=2))