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
    probability = raw_data.get('SOG') / raw_data.get('GP') * raw_data.get('SPCT')

    return data_to_return(raw_data, probability)


@FormulasRegistry.register_formula
def mean_of_goals(raw_data):
    probability = (raw_data.get('G') / raw_data.get('GP')) * 100

    return data_to_return(raw_data, probability)


@FormulasRegistry.register_formula
def player_stat_with_teams_factor(raw_data):
    probability = raw_data.get('SOG') / raw_data.get('GP') * raw_data.get('SPCT')

    teams_factor = {}
    for team, indexes in raw_data.groupby('TEAM').groups.items():
        team_data_set = raw_data.loc[indexes, ['+/-']]
        team_help_factor = float(team_data_set['+/-'].sum()) / float(len(indexes))
        teams_factor[team] = {'defence': team_help_factor, 'help': team_help_factor}

    return data_to_return(raw_data, probability, teams_factor=teams_factor)


def data_to_return(raw_data, probability, teams_factor=None):
    result_df = DataFrame({'Name': raw_data.get('PLAYER'), 'Team': raw_data.get('TEAM'),
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
