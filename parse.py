#! /usr/bin/env python
from ofxparse import OfxParser
from datetime import datetime, timedelta
import pandas as pd


ACCOUNTS = {
    '84639370':    'Checking',
    '100711877':   'Savings',
    '119500381':   'Yearly Expenses',
    '133915842':   'Income',
    '155210512':   'Andrea',
    '180173392':   'temp',
    '36003093918': 'Vacation',
    '36019456233': 'Home Improvement',
}

PAYEE = {
    'Deposit from Income': 'transfer',
    'Withdrawal to': 'transfer'
}

def set_account(acc_num):
    return 'test'


def set_payee(payee):
    for key, value in PAYEE.items():
        if key.lower() in payee.lower():
            return value
    
    return payee


ofx = OfxParser.parse(open('all360.ofx', mode='rb'))

transactions = []
for account in ofx.accounts:
    for t in account.statement.transactions:
        transactions.append([t.date.date(), set_payee(t.payee), t.type, t.amount, ACCOUNTS[account.number]])

# Set start of current week
begin = datetime.today().date() - timedelta(days=datetime.today().isoweekday() + 7)
end = begin + timedelta(days=6)

print(begin, 'to',end)

# Build pandas dataframe from OFX data
df = pd.DataFrame(data=transactions, columns=['date', 'payee', 'type', 'amount', 'account'])

spending_this_week = df[(df['date'] >= begin) & (df['date'] <= end) & (df['account'] == 'Checking') & (df['payee'] != 'transfer')]
print(spending_this_week)

print(sum(spending_this_week['amount']))

#~ df.to_pickle('df.pickle')
