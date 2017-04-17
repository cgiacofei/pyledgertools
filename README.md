# pyledgertools

## Example Config
```yaml
# Global options are applied to all sections.
global:
  rules_file: /path/to/rule/file/or/directory/.rules.d
  paystubs: /path/to/paychecks

CapOne Parent Options:
  # Plugin to use for transaction download.
  downloader: OFX Download

  # Plugin to use for parsing downloaded data.
  parser: OFX Parse

  # ofxtools config options
  url: https://ofx.capitalone360.com/OFX/ofx.html
  org: ING DIRECT
  fid: '031176110'
  appid: QWIN
  appver: '2200'
  version: '203'

  # Used in pyledgertools script
  bankid: '031176110' # This seems redundant... but currently necessary.
  
  #Login Credentials
  ofxuser: your_username
  ofxpswd: your_password

checking:
  # Inherits config from this section:
  parent: CapOne Parent Options

  # List of words to strip from payee field.
  stop_words: ['Debit Card Purchase - ']

  # Account type for ofxtools
  type: checking

  # Quotes needed to avoid issues. Particularly with leading zeroes.
  acctnum: '########'

  # Ledger account associated with this account
  from: Assets:Banks:CapOne360:Checking

  # Default account for transactions that can't be categorized automatically.
  to: Expenses:Uncategorized

  # Ledger file associated with this account.
  ledger_file: checking.ledger

savings:
  parent: CapOne Parent Options
  type: savings
  acctnum: '########'
  from: Assets:Banks:CapOne360:Savings
  to: Transfer:Unknown
  ledger_file: savings.ledger
```
