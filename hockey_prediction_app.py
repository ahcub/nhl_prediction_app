import sys
import warnings
from copy import deepcopy
from os.path import join, dirname

from PyQt4 import QtGui

from data_utils import get_raw_data, get_players_tendencies, dump_player_stats
from formulas import FormulasRegistry
from ui_utils import teams_combo_box, construct_tabs, WINDOW_HEIGHT, WINDOW_WIDTH

warnings.simplefilter(action="ignore", category=FutureWarning)

players_data_url = [
    'http://www.hokej.cz/tipsport-extraliga/player-stats/detailni?stats-menu-section=shots&stats-filter-season=2015&stats-filter-competition=5574&do=stats-view-pager-all',
    'http://www.hokej.cz/tipsport-extraliga/player-stats/detailni?stats-menu-section=radegast&do=stats-view-pager-all',
]

matches_data_url = 'http://www.hokej.cz/tipsport-extraliga/zapasy?matchList-view-displayAll=1&matchList-filter-season=2015&matchList-filter-competition=5574'

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8,uk;q=0.6,ru;q=0.4",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Cookie": "bblpasync=1449584613947; bblosync=1449585458940; __gfp_64b=sGN1O8XUlhJbt4ZWEMs2RKkIqL7nbIkleQ1NtqNQzx..M7; ibbid=BBID-01-01242986113897072; PHPSESSID=0i2j9hv3h877a3tullca1vfie4; nette-browser=gnqmgg5fbu; _ga=GA1.2.834154638.1449584608; _gat=1; __utmt=1; __utmt_trac2=1; __utma=47860542.834154638.1449584608.1449584610.1449584608.1; __utmb=47860542.4.10.1449584610; __utmc=47860542; __utmz=47860542.1449584610.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); popupShown=true; scrollingDivDisabled=true",
    "Host": "www.hokej.cz",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36",
}


class HockeyPredictionApp:
    def __init__(self):
        self.main_window = None
        self.main_layout = None
        self.tabs = None
        self.data = []
        self.team1 = None
        self.team2 = None

    def start(self):
        app = QtGui.QApplication(sys.argv)
        self.main_window = QtGui.QWidget()
        self.main_window.resize(WINDOW_HEIGHT, WINDOW_WIDTH)
        self.main_window.setWindowTitle('Hockey probability app')
        app.setWindowIcon(QtGui.QIcon(join(dirname(sys.argv[0]), 'hokey.png')))
        self.main_layout = QtGui.QVBoxLayout()
        raw_data = get_raw_data(players_data_url, matches_data_url, headers)
        raw_data_with_tendencies = get_players_tendencies(raw_data)
        dump_player_stats(raw_data_with_tendencies)
        team_names = raw_data_with_tendencies.get('Tým').unique()
        self.data = FormulasRegistry.get_processed_data_for_all_formulas(raw_data_with_tendencies)
        team_combo_box_1 = teams_combo_box(team_names)
        team_combo_box_2 = teams_combo_box(team_names)
        team_combo_box_1.currentIndexChanged['QString'].connect(self.team_combo_box_callback('team1'))
        team_combo_box_2.currentIndexChanged['QString'].connect(self.team_combo_box_callback('team2'))
        buttons_layout = QtGui.QGridLayout()
        buttons_layout.addWidget(team_combo_box_1, 0, 0)
        buttons_layout.addWidget(team_combo_box_2, 0, 1)
        calculate_btn = QtGui.QPushButton('Calculate probabilities')
        calculate_btn.clicked.connect(self.calculate_btn_callback)
        self.tabs = construct_tabs({})
        self.main_layout.addWidget(self.tabs)
        self.main_layout.addLayout(buttons_layout)
        self.main_layout.addWidget(calculate_btn)
        self.team1 = team_combo_box_1.currentText()
        self.team2 = team_combo_box_2.currentText()
        self.main_window.setLayout(self.main_layout)
        self.main_window.show()
        sys.exit(app.exec_())

    def team_combo_box_callback(self, team_name_id):
        def callback(text):
            self.__dict__[team_name_id] = text

        return callback

    def calculate_btn_callback(self):
        data_to_show = self.filter_data_to_show()
        self.tabs.setParent(None)
        self.tabs = construct_tabs(data_to_show)
        self.main_layout.insertWidget(0, self.tabs)

    def filter_data_to_show(self):
        data_to_show = {}
        for algorithm, teams_data in self.data:
            data_to_show[algorithm] = self.filter_teams(teams_data, self.team1, self.team2)

        return data_to_show

    def filter_teams(self, teams_data, *teams_filter):
        result_teams = {}
        filtered_teams_data = {team_name: team_data for team_name, team_data in teams_data.items() if team_name in teams_filter}
        team1, team2 = filtered_teams_data.keys()
        enemy_name = {team1: team2, team2: team1}
        for team_name, team_data in filtered_teams_data.items():
            players_probabilities = modify_probabilities_with_team_stats(team_data['players_stats'],
                                                                         team_data['team_stats'],
                                                                         teams_data[enemy_name[team_name]]['team_stats'])
            result_teams[team_name] = filter_players_with_default_probability_threshold(players_probabilities)
        return result_teams


def modify_probabilities_with_team_stats(player_stats, ally_team_stats, enemy_team_stats):
    result_player_stats = deepcopy(player_stats)
    if ally_team_stats and enemy_team_stats:
        supply_value = ally_team_stats['help'] - enemy_team_stats['defence']

        for player, stats in result_player_stats.items():
            stats['Probability'] += supply_value

    return result_player_stats


def filter_players_with_default_probability_threshold(players_probabilities):
    result_players = {}
    for player, stats in players_probabilities.items():
        if stats['Probability'] >= 15.0:
            result_players[player] = stats

    return result_players


if __name__ == '__main__':
    app = HockeyPredictionApp()
    app.start()
