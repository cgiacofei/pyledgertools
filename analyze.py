import yaml
import pandas as pd
import jinja2
import os, sys

INTERVALS = {
    'Weekly': 52,
    'BiWeekly': 26,
    'Monthly': 12,
    'BiMonthly': 6,
    'Yearly': 1,
}

def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


def set_type(account):
    if account.lower() == 'fixed':
        return 'Fixed'
    
    elif account.lower() == 'flex':
        return 'Flex'

    else:
        return 'Save'


with open('expenses.yml', 'r') as expense_list:
    expenses = yaml.load(expense_list)

df_exp = pd.DataFrame.from_dict(expenses, orient='columns')

df_exp['Per_Year'] = df_exp['Amount'] * [INTERVALS[x] for x in df_exp['Interval']]
df_exp['Per_Month'] = df_exp['Per_Year'] / 12
df_exp['Per_Week'] = df_exp['Per_Year'] / 52

df_exp['Class'] = [set_type(x) for x in df_exp['Account']]

df_exp = df_exp.round(0)

fixed = df_exp[df_exp['Class'] == 'Fixed']
flex = df_exp[df_exp['Class'] == 'Flex']
save = df_exp[df_exp['Class'] == 'Save']

context = {
    'data': [
        {'source': 'Fixed', 'data': fixed.to_dict(orient='records')},
        {'source': 'Flex', 'data': flex.to_dict(orient='records')},
        {'source': 'Save', 'data': save.to_dict(orient='records')}
    ]
}

weekly_fixed = df_exp[df_exp['Class'] == 'Fixed'].groupby('Account', axis=0).sum().to_dict(orient='records')
weekly_flex = df_exp[df_exp['Class'] == 'Flex'].groupby('Account', axis=0).sum().to_dict(orient='records')
weekly_save = df_exp[df_exp['Class'] == 'Save'].groupby('Account', axis=0).sum().to_dict(orient='records')

context['weekly_fixed'] = weekly_fixed
context['weekly_flex'] = weekly_flex
context['weekly_save'] = weekly_save

result = render('templates/report.html', context)
print(result)
