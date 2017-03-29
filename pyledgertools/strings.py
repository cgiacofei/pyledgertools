"""String constants."""


class UI(object):
    double_line = '=' * 80
    single_line = '- ' * 40


class Info(object):
    skip_deposit_side = 'Skip transfer deposit'
    vim_helper = '# {}\n# {} {}\n# Enter account name:\n\n'


class Prompts(object):
    needs_manual_entry = 'No matches found, enter an account name:'
    bayes_result = '[{}] {}'

    opt_e_key = 'e'
    opt_enter = '[{}] Enter New Account'.format(opt_e_key)
    opt_s_key = 's'
    opt_skip = '[{}] Skip Transaction'.format(opt_s_key)

    enter_select = 'Enter Selection: '
