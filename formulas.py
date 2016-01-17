from operator import attrgetter

from pandas import DataFrame


class FormulasRegistry:
    formulas = []

    @staticmethod
    def register_formula(formula_func):
        FormulasRegistry.formulas.append(formula_func)
        FormulasRegistry.formulas.sort(key=attrgetter('__name__'))
        return formula_func

    @staticmethod
    def get_processed_data_for_all_formulas(raw_data):
        result = []
        for formula_func in FormulasRegistry.formulas:
            result.append((formula_func.__name__, formula_func(raw_data)))
        return result


@FormulasRegistry.register_formula
def hits_count_mult_success_percent(raw_data):
    probability = raw_data.get('S/Z') * raw_data.get('RÚS')

    return data_to_return(raw_data, probability)


@FormulasRegistry.register_formula
def match_based_probabilities(raw_data):
    probability = ((raw_data.get('games_scored') / raw_data.get('games_played')) *
                   raw_data.get('current_zero_result_streak')) * 100.0

    return data_to_return(raw_data, probability)


@FormulasRegistry.register_formula
def mean_of_goals_and_shoots(raw_data):
    c1 = (raw_data.get('G') / raw_data.get('Z')) * 100
    c2 = (raw_data.get('SNB') / raw_data.get('CPS')) * 100
    probability = (c1 + c2) / 2

    return data_to_return(raw_data, probability)


@FormulasRegistry.register_formula
def player_stat_with_teams_factor(raw_data):
    probability = raw_data.get('S/Z') * raw_data.get('RÚS')

    teams_factor = {}
    for team, indexes in raw_data.groupby('Tým').groups.items():
        team_data_set = raw_data.loc[indexes, ['Z', 'ZS', '+', '-']]
        team_defence_factor = (team_data_set['ZS'] / team_data_set['Z']).sum() / 5.0
        team_help_factor = float((team_data_set['+'] - team_data_set['-']).sum()) / float(len(indexes))
        teams_factor[team] = {'defence': team_defence_factor, 'help': team_help_factor}
        print(team, team_defence_factor, team_help_factor)

    return data_to_return(raw_data, probability, teams_factor=teams_factor)


def data_to_return(raw_data, probability, teams_factor=None):
    result_df = DataFrame({'Name': raw_data.get('Jméno'), 'Team': raw_data.get('Tým'),
                           'Probability': probability, 'tendency': raw_data.get('tendency')})
    result_dict = {}
    for team, indexes in result_df.groupby('Team').groups.items():
        team_data_dicts = result_df.loc[indexes, ['Name', 'Probability', 'tendency']].set_index('Name').to_dict()
        team_result_dict = {}
        for dict_name, dict_data in team_data_dicts.items():
            for key, val in dict_data.items():
                if key not in team_result_dict:
                    team_result_dict[key] = {}
                team_result_dict[key][dict_name] = val

        team_stats = teams_factor[team] if teams_factor else None
        result_dict[team] = {'players_stats': team_result_dict, 'team_stats': team_stats}
    return result_dict
