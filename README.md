# pyledgertools
Command line tools for downloading bank data and working with ledger-cli formatted files.

## Requirements
 - [ledger](http://www.ledger-cli.org) double entry accounting
 - [ofxtools](https://github.com/csingley/ofxtools)
 - [naiveBayesClassifier](https://github.com/muatik/naive-bayes-classifier)
 - [PyYaml](https://github.com/yaml/pyyaml)

### Optional
 - [PhantomJS](http://phantomjs.org) for web scraping plugins

## Example Config
```yaml
# Global options are applied to all sections.
global:
  rules_file: /path/to/rule/file/or/directory/.rules.d
  paystubs: /path/to/paychecks

CapOne Options:
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
  
  # Login Credentials for ofx download
  ofxuser: your_username
  ofxpswd: your_password

  # Login credentials for web login
  webuser: your_username
  webpswd: your_password

checking:
  # Inherits config from this section:
  parent: CapOne Options

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
  parent: CapOne Options
  type: savings
  acctnum: '########'
  from: Assets:Banks:CapOne360:Savings
  to: Transfer:Unknown
  ledger_file: savings.ledger
```

### Config Options
*Plugins*
 - *downloader*: Plugin to use for downloading transaction data.
 - *parser*: Plugin to use for parsing downloaded data.

*Download Options*
 - *ledger_file*: Ledger file to check transactions against.
 - *dtend*: Data range end date for downloading data.
 - *dtstart*: Data range start date for downloading data.
 - *from*: Ledger account to apply transactions to.
 - to: Default ledger account if transactions not matched (not currently used).
 - *webuser*: Bank webpage login username
 - *webpswd*: Bank webpage login password

*OFX Options*
 - *ofxuser*: Bank user for OFX download.
 - *ofxpswd*: Bank password for OFX download.
 - *acctnum*: Bank account number
 - *appid*: OFX app id.
 - *appver*: OFX app version.
 - *fid*: OFX fid
 - *org*: OFX organization string.
 - *type*: Account type (checking, savings, investment).
 - *url*: URL for OFX download.
 - *version*: OFX version.

