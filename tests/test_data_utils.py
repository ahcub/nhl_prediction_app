from unittest.case import TestCase

from src.data_utils import get_teams_stats_urls, get_players_data_from_team_stats, get_raw_data


class TestDataUtils(TestCase):
    def test_get_teams_stats_urls(self):
        base = 'http://espn.go.com/nhl'
        url = '%s/teams' % base
        for team_name, team_stats_url in get_teams_stats_urls(url, {}).items():
            self.assertTrue(team_stats_url.startswith(base), 'Url: %s does not stats with %s' % (team_stats_url, base))
            print((team_name, team_stats_url))

    def test_get_players_data_from_team_stats(self):
        url = 'http://espn.go.com/nhl/teams/stats?team=Chi'
        print(get_players_data_from_team_stats('team', url, {}))

    def test_get_raw_data(self):
        all_players_stats = get_raw_data({}, {'New York Rangers': 'http://espn.go.com/nhl/teams/stats?team=NYR',
                                              'Edmonton Oilers': 'http://espn.go.com/nhl/teams/stats?team=Edm'})
        print(all_players_stats)
