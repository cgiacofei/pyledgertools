#! /usr/bin/env python3
"""Transaction classifier Implementation."""

from naiveBayesClassifier import tokenizer
from naiveBayesClassifier.trainer import Trainer
from naiveBayesClassifier.classifier import Classifier as BayesClassifier

from itertools import groupby
from math import gcd
from operator import itemgetter
import os
import re
import yaml

DOLLAR_REGEX = '([\$A_Z]+) ([\-0-9]+.[0-9]{2,2})'

# Allocation RegEx
ALLOC_REGEX = '\s+([A-Za-z0-9:_]* ?[A-Za-z0-9:_]*)\s{2,}' + DOLLAR_REGEX
TRANS_REGEX = '^\d{4,4}-\d{2,2}-\d{2,2}\s+[!\*]?\s?(?P<payee>[&#\w\s]+)'


def GCD(dollars):
    """Find greatest common divisor of list of dollar ammounts.

    Works with integer and floats.

    Parameters:
        dollars (list): Values to find the common denominator.
    """

    # Convert dollar values to integers
    dollars = [int(d * 100) for d in dollars]

    res = dollars[0]

    for c in dollars[1::]:
        res = gcd(res, c)

    return res / 100


def train_journal(journal_string):
    """Generate training data from ledger entries."""

    blocks = [x.split('\n') for x in journal_string.split('\n\n')]

    training_data = []

    for tran in blocks:
        tran = [x for x in tran if x != '' and not x.startswith(';')]

        if len(tran) > 0:
            result = re.search(TRANS_REGEX, tran[0])
            if result:
                payee = result.group('payee')

            result = re.findall(ALLOC_REGEX, ' '.join(tran[1:]))

            if len(result) > 0:
                alloc_list = list(result[1])
                alloc_list[2] = float(alloc_list[2])
                alloc_list[0] = alloc_list[0].strip()

                training_data.append([payee] + alloc_list)

    sorted_data = sorted(training_data, key=itemgetter(1))
    sorted_data = groupby(sorted_data, itemgetter(1))

    return_data = []
    for elmnt, items in sorted_data:
        grp_tran = [v for v in items]
        return_data.append([elmnt, grp_tran, GCD([v[3] for v in grp_tran])])

    return return_data


class Classifier(object):
    """Custom class to implement naive bayes classification using
    naiveBayesClassifier.

    Attributes:
        classifier (Classifier object): Object of class `Classifier` for
            classifying transactios based on existing journal.
    """

    class NotImplemented(Exception):
        pass

    def __init__(self, journal_file=None, rules=None):
        """Classifer initialization.

        Parameters:
            journal_file (str): Path to journal file to import.
            rules_file (str): Path to rules.
        """

        if journal_file is not None:
            self._tknizer = tokenizer.Tokenizer(signs_to_remove=['?!%'])

            self._trainer = Trainer(self._tknizer)

            with open(journal_file) as journal:
                journal_string = journal.read()

            journal_data = train_journal(journal_string)

            for group in journal_data:
                # 0: Allocation account.
                # 1: List of transactions.
                # 2: Greatest common multiple of values in transactions.
                for transaction in group[1]:
                    # 0: Transaction payee string.
                    # 1: Allocation account.
                    self._trainer.train(transaction[0], transaction[1])

            self._classifier = BayesClassifier(
                self._trainer.data,
                self._tknizer
            )
        else:
            self._classifier = None

        if rules is not None:
            # Process rules file
            if os.path.isfile(rules):
                rules = yaml.load(open(rules))

            # If directory is given find all .rules files in directory
            # and build a single dictionary from their contents.
            elif os.path.isdir(rules):
                self._rules = {}
                for root, dirs, files in os.walk(rules):
                    for file in files:
                        if file.endswith('.rules'):
                            f = yaml.load(open(os.path.join(root, file)))
                            self._rules.update(f)
        else:
            self._rules = None

    def add_data(self, text, category):
        """Update training data with new examples.
        
        Adds new data to the trainer then generates a new classifier. Can be
        useful for updating on the fly if performing an interactive data import.

        Parameters:
            text (str): New text to classify.
            category (str): Classification of `text`.
        """
        self._trainer.train(text, category)
        self._classifier = BayesClassifier(
            self._trainer.data,
            self._tknizer
        )

    def classify(self, text, method='bayes'):
        """Give classifcation for a text string using bayes classification.

        Parameters:
            text (str): Text to classify.
            method (str): Type of classification to use. Default to `bayes`.
        Returns:
            list: Available categories and their probabilities.
        """

        if method == 'bayes':
            return self._classifier.classify(text)
        elif method == 'rules':
            raise NotImplementedError(
                'Classification based on rules file not yet implemented'
            )
        else:
            raise NotImplemented('The method `{}` is not valid'.format(method))
