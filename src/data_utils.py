import re
import sys
from ast import literal_eval
from os import remove
from os.path import isfile, abspath, dirname, join
from urllib.parse import urljoin, urlparse, urlunparse

import pandas as pd
import requests
from html_table_parser import HTMLTableParser
from lxml.html import fromstring, tostring

DATA_FILE = join(dirname(abspath(sys.argv[0])), 'data.txt')
TEAMS_FILE = join(dirname(abspath(sys.argv[0])), 'teams.txt')


def get_raw_data(headers, teams):
    return pd.concat(get_players_dataframes(teams, headers), ignore_index=True)


def get_players_dataframes(teams_stats_urls, headers):
    for team_name, team_stats_url in teams_stats_urls.items():
        yield get_players_data_from_team_stats(team_name, team_stats_url, headers)


def get_teams_stats_urls(teams_list_url, headers):
    teams_stats_urls = {}
    launch_counter = 0
    if isfile(TEAMS_FILE):
        launch_counter, teams_stats_urls = get_teams_from_file(teams_stats_urls)

    if not isfile(TEAMS_FILE):
        domain = get_url_site(teams_list_url)

        for element in get_html_page(teams_list_url, headers).xpath('//*[@id="content"]/div/div/div/div/div/div/ul/li'):
            team_name = element.find('div/h5').text_content().strip()

            re_pattern = re.compile(r'=("|\')(/nhl/teams/stats\?team=\w\w\w)("|\')')
            for team_stat_url in re_pattern.finditer(tostring(element).decode()):
                teams_stats_urls[team_name] = urljoin(domain, team_stat_url.group(2))

            launch_counter = 0

    with open(TEAMS_FILE, 'w') as teams_file:
        teams_file.write(str(launch_counter))
        teams_file.write(str(teams_stats_urls))

    return teams_stats_urls


def get_teams_from_file(teams_stats_urls):
    try:
        with open(TEAMS_FILE) as teams_file:
            launch_counter = literal_eval(teams_file.readline())
            launch_counter += 1
            teams_stats_urls = literal_eval(teams_file.readline())
    except Exception:
        remove(TEAMS_FILE)
        return  0, {}
    else:
        if launch_counter > 10:
            remove(TEAMS_FILE)
            teams_stats_urls = {}
        return launch_counter, teams_stats_urls


def get_players_data_from_team_stats(team_name, team_stats_url, headers):
    html_page = get_html_page(team_stats_url, headers)

    team_players_stats = html_page.find_class('tablehead')

    players_stats = []
    players_data_columns = []
    for table in team_players_stats:
        for redundant_el in table.find_class('stathead'):
            redundant_el.getparent().remove(redundant_el)
        table_string = tostring(table, encoding='utf-8')
        table_parser = HTMLTableParser()
        table_parser.feed(table_string.decode('utf-8'))
        if table_parser.tables[0][0][0] == 'PLAYER' and 'SOG' in table_parser.tables[0][0]:
            players_data_columns = table_parser.tables[0][0]
            for row in table_parser.tables[0][1:]:
                row[0] = extract_player_name(row[0])
                row.append(team_name)
                players_stats.append(row)
            break
    players_data_columns.append('TEAM')
    result_df = pd.DataFrame(columns=players_data_columns, data=players_stats)
    return result_df.apply(pd.to_numeric, errors='ignore')


def get_url_site(url):
    return urlunparse(urlparse(url)[:2] + ('',) * 4)


def get_html_page(url, headers):
    request_result = requests.get(url, headers=headers)
    return fromstring(request_result.content)


def get_match_html_page(site, match_url_path, headers):
    url = urljoin(site, match_url_path)
    return get_html_page(url, headers)


def extract_player_name(player_info):
    return player_info.split(',')[0].strip()


def get_players_tendencies(data):
    data['tendency'] = 'no_change'
    data['tendency_value'] = data['G'] / data['GP']
    if isfile(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8') as data_file:
            prev_data = literal_eval(data_file.read())
            for row_index, data_series in data.iterrows():
                if data_series['TEAM'] in prev_data and data_series['PLAYER'] in prev_data[data_series['TEAM']]:
                    player_stats = prev_data[data_series['TEAM']][data_series['PLAYER']]
                    value = player_stats['tendency_value']
                    difference = (data_series['G'] / data_series['GP']) - value
                    if difference:
                        data.loc[row_index, 'tendency'] = 'up' if difference > 0.0 else 'down'
                    else:
                        data.loc[row_index, 'tendency'] = player_stats['tendency']

    return data


def dump_player_stats(data):
    if isfile(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8') as data_file:
                prev_data = literal_eval(data_file.read())
    else:
        prev_data = {}
    result_dict = prev_data
    for team, indexes in data.groupby('TEAM').groups.items():
        team_data_dicts = data.loc[indexes, ['PLAYER', 'tendency_value', 'tendency']].set_index('PLAYER').to_dict()
        team_result_dict = {}
        for dict_name, dict_data in team_data_dicts.items():
            for key, val in dict_data.items():
                if key not in team_result_dict:
                    team_result_dict[key] = {}
                team_result_dict[key][dict_name] = val
        result_dict[team] = team_result_dict

    with open(DATA_FILE, 'w', encoding='utf-8') as data_file:
        data_file.write(str(result_dict))
