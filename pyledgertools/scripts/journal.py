from argparse import ArgumentParser

def sort_journal():
    """Sort journal file transactions."""

    parser = ArgumentParser()

    parser.add_argument(
        '-j', '--journal-file',
        dest='journal_file',
        default=None,
        help='Journal file to be sorted.'
    )
    args = dict((k, v) for k, v in vars(parser.parse_args()).items() if v)
    journal_file = args.get('journal_file')

    with open(journal_file, 'r') as infile:
        journal_string = infile.read()

    blocks = [x for x in journal_string.split('\n\n')]

    blocks.sort()

    for tran in blocks:
        print(tran + '\n')
