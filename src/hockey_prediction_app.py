import sys
from copy import deepcopy
from os.path import join, dirname

from PyQt4 import QtGui

from src.data_utils import get_teams_stats_urls, get_raw_data, get_players_tendencies, \
    dump_player_stats
from src.formulas import FormulasRegistry
from src.ui_utils import teams_combo_box, construct_tabs, WINDOW_HEIGHT, WINDOW_WIDTH

teams_list_url = 'http://espn.go.com/nhl/teams'

headers = {

}


class HockeyPredictionApp:
    def __init__(self):
        self.main_window = None
        self.main_layout = None
        self.tabs = None
        self.team1 = None
        self.team2 = None
        self.teams = {}

    def start(self):
        app = QtGui.QApplication(sys.argv)
        self.main_window = QtGui.QWidget()
        self.main_window.resize(WINDOW_HEIGHT, WINDOW_WIDTH)
        self.main_window.setWindowTitle('Hockey probability app')
        app.setWindowIcon(QtGui.QIcon(join(dirname(sys.argv[0]), 'hokey.png')))
        self.main_layout = QtGui.QVBoxLayout()

        self.teams = get_teams_stats_urls(teams_list_url, headers)

        team_names = [team_name for team_name, _ in self.teams.items()]
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
        raw_data_to_show = self.get_team_data_to_show()
        data_to_show = filter_data_to_show(raw_data_to_show)
        self.tabs.setParent(None)
        self.tabs = construct_tabs(data_to_show)
        self.main_layout.insertWidget(0, self.tabs)

    def get_team_data_to_show(self):
        teams = {team_name: team_url for team_name, team_url in self.teams.items()
                 if team_name in [self.team1, self.team2]}
        raw_data = get_raw_data(headers, teams)
        raw_data_with_tendencies = get_players_tendencies(raw_data)
        dump_player_stats(raw_data_with_tendencies)
        data = FormulasRegistry.get_processed_data_for_all_formulas(raw_data_with_tendencies)
        return data


def filter_data_to_show(data):
    data_to_show = {}
    for algorithm, teams_data in data:
        data_to_show[algorithm] = filter_teams(teams_data)

    return data_to_show


def filter_teams(teams_data):
    result_teams = {}
    team1, team2 = teams_data.keys()
    enemy_name = {team1: team2, team2: team1}
    for team_name, team_data in teams_data.items():
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
