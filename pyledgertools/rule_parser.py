
# Comparison functions
# Dates used as strings in format YYYY-MM-DD so string comparison can be used
def CONTAINS(rule_value, tran_value):
    """Return True if rule_value contained in tran_value
    """

    rule_value = rule_value.lower()
    tran_value = tran_value.lower()

    return tran_value.find(rule_value) >= 0


def STARTS_WITH(rule_value, tran_value):
    """Return True if tran_value starts with rule_value
    """

    rule_value = rule_value.lower()
    tran_value = tran_value.lower()

    tran_value = tran_value.strip()
    return tran_value.startswith(rule_value)


def ENDS_WITH(rule_value, tran_value):
    """Return True if tran_value ends with rule_value
    """

    rule_value = rule_value.lower()
    tran_value = tran_value.lower()

    tran_value = tran_value.strip()
    return tran_value.endswith(rule_value)


def EQUALS(rule_value, tran_value):
    """Return True if rule_value is euqal to tran_value.  Works for both
    numbers and strings
    """

    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value == tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        tran_value = tran_value.strip()

        return rule_value == tran_value


def GT(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value < tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value < tran_value


def GE(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value <= tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value <= tran_value


def LT(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value > tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value > tran_value


def LE(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value >= tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value >= tran_value


def MOD(rule_value, tran_value):
    modulus = float(tran_value) % float(rule_value)

    if modulus == 0:
        return True

    return False


# Boolean logic functions
def AND(bools):
    """Logical And."""
    if False in bools:
        return False

    return True


def OR(bools):
    """Logical OR."""
    if True in bools:
        return True

    return False


def NAND(bools):
    return not AND(bools)


def NOR(bools):
    return not OR(bools)


def XOR(bools):
    """Logical Xor.
       Result is True if there are an odd number of true items
       and False if there are an even number of true items.
    """
    # Return false if there are an even number of True results.
    if len([x for x in bools if x == True]) % 2 == 0:
        return False

    return True


def build_rules(rule_loc):
    """Build rules from file or directory."""
    if os.path.isfile(rule_loc):
        rules = load(open(rule_loc))

    # If directory is given find all .rules files in directory
    # and build a single dictionary from their contents.
    elif os.path.isdir(rule_loc):
        rules = {}
        for root, dirs, files in os.walk(rule_loc):
            for file in files:
                if file.endswith('.rules'):
                    rules.update(load(open(os.path.join(root, file))))

    return rules


def make_rule(payee, account):
    payee = re.sub('[^a-zA-Z0-9 \n\.,]', '', payee)

    rule_template = """---
        '{name}':
          Change_Payee: False
          Conditions:
            - AND:
              - PAYEE CONTAINS {payee}
          Allocations:
            - 100 PERCENT {account}
        """
    rule_string = rule_template.format(
        name=payee,
        payee=payee,
        account=account
    )

    rule_yml = yaml.load(rule_string)

    return rule_yml[payee]


def check_condition(condition, trans_obj):
    """Convert the condition string from the rule into the
    appropriate function and evaluate it.
    """
    condition = condition.split(' ')

    field = condition[0]
    test = condition[1]
    test_value = ' '.join(condition[2:])

    # Use string value to access comparison function
    # sys.module[__name__] returns this module
    test_func = getattr(sys.modules[__name__], test)

    try:
        field_value = trans_obj[FIELDS[field]]
    except:
        field_value = ''

    return test_func(test_value, field_value)


def walk_rules(conditions, trans_obj=None, logic=None):
    results = []

    for condition in conditions:
        if isinstance(condition, dict):
            new_logic = list(condition.keys())[0]
            res = walk_rules(condition[new_logic], trans_obj, new_logic)
        if isinstance(condition, str):
            res = check_condition(condition, trans_obj)

        results.append(res)

    # Evaluate results
    l_func = getattr(sys.modules[__name__], logic)
    final = l_func(results)

    return final
