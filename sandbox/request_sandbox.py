import requests

request_url = "http://espn.go.com/nhl/teams/stats?team=StL"

response = requests.get(url=request_url)

print(response.content.decode())
