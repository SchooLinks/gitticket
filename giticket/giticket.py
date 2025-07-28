# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import io
import re
import subprocess
import sys

import six

underscore_split_mode = 'underscore_split'
regex_match_mode = 'regex_match'

# Allowed commit types (always converted to lowercase)
ALLOWED_TYPES = [
    'build',
    'chore',
    'ci',
    'docs',
    'feat',
    'fix',
    'perf',
    'refactor',
    'revert',
    'style',
    'test',
    'enh'
]

# Allowed commit scopes (always converted to uppercase)
ALLOWED_SCOPES = [
    "AL",
    "ASM",
    "AUTH",
    "BADGE",
    "BASE",
    "CAM",
    "CAR",
    "CFG",
    "CHECK",
    "COMMENT",
    "CP",
    "CSL",
    "CTE",
    "DMD",
    "DOC",
    "DP",
    "DS",
    "DU",
    "ELE",
    "ES",
    "EXDS",
    "EXP",
    "FAFSA",
    "FEED",
    "FNL",
    "FORM",
    "GEO",
    "GOAL",
    "GOL",
    "GUARD",
    "I18N",
    "ILP",
    "IPDB",
    "IPPM",
    "IS",
    "K12ADMIN",
    "KRI",
    "LNP",
    "MEET",
    "MEMBER",
    "MNGMT",
    "MSG",
    "NCAA",
    "NOTE",
    "NOTIF",
    "ONB",
    "OPPS",
    "ORGPROF",
    "PROF",
    "QNA",
    "RC",
    "RDC",
    "RES",
    "RLBS",
    "RLP",
    "RONTAG",
    "ROS",
    "SCG",
    "SCHOL",
    "SCORE",
    "SDH",
    "SET",
    "SIS",
    "SS",
    "STATS",
    "STDH",
    "SYE",
    "TAG",
    "TODO",
    "UI",
    "VR",
]


def update_commit_message(filename, regex, mode, format_string):
    with io.open(filename, 'r+') as fd:
        contents = fd.readlines()
        commit_msg = contents[0].rstrip('\r\n')
        # Check if we can grab ticket info from branch name.
        branch = get_branch_name()

        # Bail if commit message starts with “fixup!” or commit message already contains tickets
        if commit_msg.startswith('fixup!') or any(re.search(regex, content) for content in contents):
            return

        tickets = re.findall(regex, branch)
        if tickets:
            if mode == underscore_split_mode:
                tickets = [branch.split(six.text_type('_'))[0]]
            tickets = [t.strip() for t in tickets]

            # Parse commit message for conventional commit structure
            # Expected format: "type(scope): message"
            type_scope_pattern = r'^([a-zA-Z]+)\(([a-zA-Z0-9]+)\):\s*(.*)$'
            match_res = re.match(type_scope_pattern, commit_msg)

            if match_res:
                # Extract parts from the regex match
                commit_type = match_res.group(1).lower()  # Convert type to lowercase
                commit_scope = match_res.group(2).upper()  # Convert scope to uppercase
                commit_message = match_res.group(3)

                # Validate commit type
                if commit_type not in ALLOWED_TYPES:
                    sys.stderr.write(f"Error: Invalid commit type '{commit_type}'. Allowed types are: {', '.join(ALLOWED_TYPES)}\n")
                    sys.exit(1)

                # Validate commit scope
                if commit_scope not in ALLOWED_SCOPES:
                    sys.stderr.write(f"Error: Invalid commit scope '{commit_scope}'. Allowed scopes are: {', '.join(ALLOWED_SCOPES)}\n")
                    sys.exit(1)

                # Format as conventional commit: type(scope): ticket message
                new_commit_msg = "{type}({scope}): {ticket} {message}".format(
                    type=commit_type,
                    scope=commit_scope,
                    ticket=tickets[0],
                    message=commit_message
                )
            else:
                # If the format doesn't match, inform the user about the expected format
                sys.stderr.write("Error: Commit message must follow the format 'type(scope): message'\n")
                sys.stderr.write(f"Allowed types: {', '.join(ALLOWED_TYPES)}\n")
                sys.stderr.write(f"Allowed scopes: {', '.join(ALLOWED_SCOPES)}\n")
                sys.exit(1)

            contents[0] = six.text_type(new_commit_msg + "\n")
            fd.seek(0)
            fd.writelines(contents)
            fd.truncate()


def get_branch_name():
    # Only git support for right now.
    return subprocess.check_output(
        [
            'git',
            'rev-parse',
            '--abbrev-ref',
            'HEAD',
        ],
    ).decode('UTF-8')


def main(argv=None):
    """This hook saves developers time by prepending ticket numbers to commit-msgs.
    For this to work the following two conditions must be met:

        - The ticket format regex specified must match.
        - The branch name format must be <ticket number>_<rest of the branch name>
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='+')
    parser.add_argument('--regex')
    parser.add_argument('--format')
    parser.add_argument('--mode', nargs='?', const=underscore_split_mode,
                        default=underscore_split_mode,
                        choices=[underscore_split_mode, regex_match_mode])
    args = parser.parse_args(argv)
    regex = args.regex or r'[A-Z]+-\d+'  # noqa
    format_string = args.format or '{ticket} {commit_msg}' # noqa
    update_commit_message(args.filenames[0], regex, args.mode, format_string)


if __name__ == '__main__':
    sys.exit(main())
