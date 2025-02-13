# Constants
import os
from urllib.parse import urlencode

import geocoder
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

@bedrock_agent_tool(action_group="LocationToolsActionGroup")
def search_near(what: str, where: str=None) -> str:
    """Search for places near a particular named region or point. Either the
    region must be specified with the near parameter, or a circle around a point
    must be specified with the ll and radius parameters.

    Always call me with a named region and not a latitude or longitude. If you have a latitude and longitude,
    then call sn.

    Args:
        what: concept you are looking for (e.g., coffee shop, Hard Rock Cafe)
        where: a geographic region (e.g., Los Angeles or Fort Greene), this must be a named region.
    """
    params = {
        "query": what,
        "limit": 5,
        "near": where
    }

    return submit_request("/places/search", params, version20241206=True)

@bedrock_agent_tool(action_group="LocationToolsActionGroup")
def get_location() -> str:
    """Get user's location. Returns latitude and longitude, or else reports it could not find location. Tries to guess user's location
      based on ip address. Useful if the user has not provided their own precise location.

    """

    location = geocoder.ip('me')

    if not location.ok:
        return "I don't know where you are"

    return f"{location.lat},{location.lng} (using geoip, so this is an approximation)"

@bedrock_agent_tool(action_group="LocationToolsActionGroup")
def place_from_latitude_and_longitude(ll: str) -> str:
    """Get the most likely place the user is at based on their reported location. This returns the geographic
    area by name.
    Args:
        ll: comma separate latitude and longitude pair (e.g., 40.74,-74.0)
    """
    params = {
        "ll": ll,
        "limit": 1
    }
    return submit_request("/v3/places/nearby", params, version20241206=False)


@bedrock_agent_tool(action_group="LocationToolsActionGroup")
def place_details(fsq_place_id: str) -> str:
    """
        Get detailed information about a place based on the fsq_id (foursquare id), including:
       description, phone, website, social media, hours, popular hours, rating (out of 10),
       price, menu, top photos, top tips (reviews from users), top tastes, and features
       such as takes reservations.
    Args:
        fsq_place_id: foursquare id (foursquare id) of the place which is returned from search_near.

    """

    params = {
      "fields": "description,tel,website,social_media,hours,hours_popular,rating,price,menu,photos,tips,tastes,features"
    }

    return submit_request(f"/v3/places/{fsq_place_id}", params, version20241206=False)



if __name__ == "__main__":
    print(search_near("Italian Restaurants", "Seattle"))