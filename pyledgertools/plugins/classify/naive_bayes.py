#! /usr/bin/env python3
"""Transaction classifier Implementation."""

from naiveBayesClassifier import tokenizer
from naiveBayesClassifier.trainer import Trainer
from naiveBayesClassifier.classifier import Classifier as BayesClassifier
from yapsy.IPlugin import IPlugin
from itertools import groupby

from operator import itemgetter
import re

from pyledgertools.functions import amount_group, GCD

DOLLAR_REGEX = '([\$A-Z]+)?\s?([\-0-9]+.[0-9]{2,2})?'

# Allocation RegEx
ALLOC_REGEX = '\s+([A-Za-z0-9:_-]* ?[A-Za-z0-9:_-]*)\s*' + DOLLAR_REGEX
TRANS_REGEX = '^\d{4,4}[/-]{1,1}\d{2,2}[/-]{1,1}\d{2,2}\s+[!\*]?\s?(?P<payee>[&#\w\s]+)'


def train_journal(journal_string):
    """Generate training data from ledger entries."""
    blocks = [x.split('\n') for x in journal_string.decode('utf-8').split('\n\n')]
    training_data = []

    for tran in blocks:
        tran = [x.split('=')[0] for x in tran if x != '' and not re.match('\s*;',x)]
        if len(tran) > 0:
            result = re.search(TRANS_REGEX, tran[0])
            if result:
                payee = result.group('payee')

            result = re.findall(ALLOC_REGEX, ' '.join(tran[1:]))
            if len(result) > 1:
                alloc_list = list(result[1])
                alloc_list[2] = float(result[0][2])
                alloc_list[0] = alloc_list[0].strip()
                payee += ' ' + amount_group(alloc_list[2])
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

    def __init__(self, journal=None):
        """Classifer initialization.

        Parameters:
            journal_file (str): Journal file string to import.
        """
        self._tknizer = tokenizer.Tokenizer(signs_to_remove=['?!%.'])
        self._trainer = Trainer(self._tknizer)
        if journal is not None:
            journal_data = train_journal(journal)

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

    def update(self, text, category):
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
            if self._classifier is not None:
                return self._classifier.classify(text)
            else:
                return None

        elif method == 'rules':
            raise NotImplementedError(
                'Classification based on rules file not yet implemented'
            )
        else:
            raise NotImplemented('The method `{}` is not valid'.format(method))


class PluginLoader(IPlugin):
    def setup(self, journal_file=None):
        return Classifier(journal_file)
