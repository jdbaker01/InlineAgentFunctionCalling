# Constants
import os

import httpx
from function_calls import bedrock_agent_tool, get_bedrock_tools
import json

WEATHER_API = "https://api.weather.gov"

API_EMAIL = os.getenv("WEATHER_API_EMAIL")

def submit_request(url: str) -> str:
    headers = {
        "User-Agent": API_EMAIL,
    }
    with httpx.Client() as client:
        try:
            print(url)
            response = client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(e)
            return "Could not retrieve weather data"

@bedrock_agent_tool(action_group="WeatherToolsActionGroup")
def get_weather(lat: float, lng: float) -> str:
    """Get the weather forecast for a point specified by latitude and longitude.

    Args:
        lat: latitude
        lng: longitude
    """

    def strip_trailing_zeros(n):
        return format(float(n), ".3f").rstrip('0').rstrip('.') if '.' in str(n) else str(n)

    point_endpoint = f"{WEATHER_API}/points/{strip_trailing_zeros(lat)},{strip_trailing_zeros(lng)}"
    point_res = submit_request(point_endpoint)
    print(point_res)
    point_json = json.loads(point_res)
    gridId = point_json["properties"]["gridId"]
    gridX = point_json["properties"]["gridX"]
    gridY = point_json["properties"]["gridY"]
    forecast_hourly_endpoint = point_json["properties"]["forecastHourly"]
    observation_stations_endpoint = point_json["properties"]["observationStations"]
    stations_json = json.loads(submit_request(observation_stations_endpoint))

    if stations_json["features"] == []:
        return "No weather stations found near this location"

    def get_estimated_distance(slat: float, slng: float) -> float:
        return (float(slat) - float(lat)) ** 2 + (float(slng) - float(lng)) ** 2

    # Find the closest station
    # Note: closest station may have incomplete readings. Could improve by falling back to next closest station
    # (Airport stations seem to have better coverage)
    closest_station = sorted(stations_json["features"], key=lambda x: get_estimated_distance(x["geometry"]["coordinates"][1], x["geometry"]["coordinates"][0]))[0]
    stationIdentifier = closest_station["properties"]["stationIdentifier"]
    weather_endpoint = f"{WEATHER_API}/stations/{stationIdentifier}/observations/latest"

    weather_json = json.loads(submit_request(weather_endpoint))
    forecast_json = json.loads(submit_request(forecast_hourly_endpoint))

    temp_c = weather_json["properties"]["temperature"]["value"]
    wind_speed = weather_json["properties"]["windSpeed"]["value"]
    wind_chill = weather_json["properties"]["windChill"]["value"]
    precipitation = weather_json["properties"]["precipitationLastHour"]["value"]

    simple_forecast = [
        {
            "time": period["startTime"],
            "temp": f'{period["temperature"]}{period["temperatureUnit"]}',
            "precipitation": f'{period["probabilityOfPrecipitation"]["value"]}%',
            "windSpeed": period["windSpeed"],
            "shortForecast": period["shortForecast"]
        }
        for period in forecast_json["properties"]["periods"]
    ]

    return json.dumps({
        "tempCelsuis": temp_c,
        "windSpeed": wind_speed,
        "windChill": wind_chill,
        "precipitation": precipitation,
        "forecast": simple_forecast
    })
