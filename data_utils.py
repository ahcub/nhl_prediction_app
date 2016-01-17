import re
import sys
from ast import literal_eval
from datetime import datetime
from os.path import dirname, join, isfile
from urllib.parse import urljoin, urlparse, urlunparse

import pandas as pd
import requests
from html_table_parser import HTMLTableParser
from lxml import html
from lxml.html import fromstring, tostring

DATA_FILE = 'data.txt'


def get_raw_data(players_data_url, matches_data_url, headers):
    match_based_data = get_players_data_from_matches_stats(matches_data_url, headers)
    players_stats_data = get_players_data_by_their_stats(players_data_url, headers)
    raw_data_df = match_based_data.merge(players_stats_data, left_index=True, right_on='Jméno')
    return raw_data_df.convert_objects(convert_numeric=True)


def get_players_data_from_matches_stats(matches_data_url, headers):
    matches_info = get_matches_info(matches_data_url, headers)
    players_stat = {}
    sorted_matches_info = sorted(matches_info, key=key_getter)
    for match_info in sorted_matches_info:
        for player in match_info['match_players']:
            if player not in players_stat:
                players_stat[player] = {
                    'games_played': 0,
                    'games_scored': 0,
                    'current_zero_result_streak': 0
                }

            players_stat[player]['games_played'] += 1
            if player in match_info['players_scored']:
                players_stat[player]['games_scored'] += 1
                players_stat[player]['current_zero_result_streak'] = 0
            else:
                players_stat[player]['current_zero_result_streak'] += 1

    return pd.DataFrame.from_dict(players_stat, orient='index')


def key_getter(item):
    return datetime.strptime(item['date'], '%d.%m.%Y')


def get_matches_info(url, headers):
    registry_file_path = join(dirname(sys.argv[0]), 'matches_registry.txt')
    matches_info = []
    if isfile(registry_file_path):
        with open(registry_file_path, encoding='utf-8') as registry_file:
            file_content = registry_file.read()
            if file_content:
                matches_info = literal_eval(file_content)

    processed_matches = set([match_info['match_id'] for match_info in matches_info])
    site = get_url_site(url)
    for match_url_path in get_hockey_matches(url, headers):
        if match_url_path not in processed_matches:
            html_page = get_match_html_page(site, match_url_path, headers)
            match_players = get_match_players(html_page)
            if match_players:
                matches_info.append({
                    'match_id': match_url_path,
                    'date': get_match_date(html_page),
                    'players_scored': get_payers_scored(html_page),
                    'match_players': match_players,
                })
    with open(registry_file_path, 'w', encoding='utf-8') as registry_file:
        registry_file.write(str(matches_info))
    return matches_info


def get_url_site(url):
    return urlunparse(urlparse(url)[:2] + ('',) * 4)


def get_hockey_matches(url, headers):
    request_result = requests.get(url, headers=headers)
    html_page = fromstring(request_result.content)
    matches_table = html_page.find_class('preview m-b-30')
    for matches_group in matches_table:
        for match_info in matches_group.findall('tbody/tr'):
            if match_info.find_class('preview__period'):
                pattern = re.compile(r'"(\\/\w+\\/\d+)"')
                match = pattern.search(match_info.attrib['onclick']).group(1).replace('\\', '')
                yield match


def get_match_html_page(site, match_url_path, headers):
    url = urljoin(site, match_url_path)
    request_result = requests.get(url, headers=headers)
    return fromstring(request_result.content)


def get_match_date(html_page):
    found_elements = html_page.find_class('col-100 heading')
    for el in found_elements:
        for li_element in el.findall('ul/li'):
            pattern = re.compile(r'(\d+\.\d+\.\d+)')
            search_result = pattern.search(li_element.text_content())
            if search_result is not None:
                return search_result.group()


def get_payers_scored(html_page):
    score_tables = html_page.find_class('table-last-right')

    players_scored = set()
    for table in score_tables:
        for redundant_el in table.find_class('row-plus-minus'):
            redundant_el.getparent().remove(redundant_el)
        table_string = tostring(table, encoding='utf-8')
        table_parser = HTMLTableParser()
        table_parser.feed(table_string.decode('utf-8'))
        for row in table_parser.tables[0][1:]:
            if len(row) > 3:
                players_scored.add(extract_player_name(row[2]))

    return players_scored


def extract_player_name(player_info):
    player_name_els = player_info.split(' (')[0].split()
    processed_player_name_els = [name_el.lower().capitalize() for name_el in player_name_els]
    return ' '.join(processed_player_name_els)


def get_match_players(html_page):
    match_players = set()
    players_tables_containers = html_page.find_class('col-soupisky-home') + html_page.find_class('col-soupisky-visitor')
    for tables_container in players_tables_containers:
        for table in tables_container.findall('table'):
            table_string = tostring(table, encoding='utf-8')
            table_parser = HTMLTableParser()
            table_parser.feed(table_string.decode('utf-8'))
            for row in table_parser.tables[0][1:]:
                if row[0]:
                    match_players.add(extract_player_name(row[2]))
    return match_players


def get_players_data_by_their_stats(players_data_url, headers):
    if isinstance(players_data_url, list):
        urls_to_process = players_data_url
    else:
        urls_to_process = [players_data_url]

    result_df = None
    for url in urls_to_process:
        response = requests.get(url, headers=headers)
        doc = html.fromstring(response.text)
        data_table_elements = doc.find_class('table-stats')
        table_string = html.tostring(data_table_elements[0], encoding='utf-8').decode()
        html_table_parser = HTMLTableParser()
        html_table_parser.feed(table_string)
        data_table = html_table_parser.tables[0]
        df = pd.DataFrame(data_table[1:], columns=data_table[0])
        if result_df is None:
            result_df = df
        else:
            merge_on = ['Jméno', 'Tým', 'Z']
            result_df = result_df.merge(df, left_on=merge_on, right_on=merge_on, )
    return result_df


def get_players_tendencies(data):
    data['tendency'] = 'no_change'
    if isfile(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8') as data_file:
            prev_data = literal_eval(data_file.read())
            for row_index, data_series in data.iterrows():
                if data_series['Tým'] in prev_data and data_series['Jméno'] in prev_data[data_series['Tým']]:
                    player_stats = prev_data[data_series['Tým']][data_series['Jméno']]
                    value = player_stats['SNB/Z']
                    difference = data_series['SNB/Z'] - value
                    if difference:
                        data.loc[row_index, 'tendency'] = 'up' if difference > 0.0 else 'down'
                    else:
                        data.loc[row_index, 'tendency'] = player_stats['tendency']

    return data


def dump_player_stats(data):
    result_dict = {}
    for team, indexes in data.groupby('Tým').groups.items():
        team_data_dicts = data.loc[indexes, ['Jméno', 'SNB/Z', 'tendency']].set_index('Jméno').to_dict()
        team_result_dict = {}
        for dict_name, dict_data in team_data_dicts.items():
            for key, val in dict_data.items():
                if key not in team_result_dict:
                    team_result_dict[key] = {}
                team_result_dict[key][dict_name] = val
        result_dict[team] = team_result_dict

    with open(DATA_FILE, 'w', encoding='utf-8') as data_file:
        data_file.write(str(result_dict))
