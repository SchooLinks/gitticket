from __future__ import absolute_import
from __future__ import unicode_literals

import mock
import pytest
import six

from giticket.giticket import get_branch_name
from giticket.giticket import main
from giticket.giticket import update_commit_message
from giticket.giticket import find_closest_match
from giticket.giticket import ALLOWED_TYPES
from giticket.giticket import ALLOWED_SCOPES

TESTING_MODULE = 'giticket.giticket'

COMMIT_MESSAGE = 'Test commit message\n\nFoo bar\nBaz qux'


@pytest.mark.parametrize('msg', (
    'Test ABC-1 message',
    'ABC-2 Test message',
    'Test message ABC-3',
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_no_modification(mock_branch_name, msg, tmpdir):
    mock_branch_name.return_value = 'JIRA-1234_new_feature'
    path = tmpdir.join('file.txt')
    path.write(msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'underscore_split', '{ticket} {commit_msg}')
    # Message should remain intact as it contains some ticket
    assert path.read() == msg


@pytest.mark.parametrize('test_data', (
    ('JIRA-1234', 'JIRA-1234'),
    ('JIRA-1234_bar', 'JIRA-1234'),
    ('foo-JIRA-1234_bar', 'foo-JIRA-1234'),
    ('foo/JIRA-1234-bar', 'foo/JIRA-1234-bar'),
    ('foo_JIRA-1234_bar', 'foo'),
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_underscore_split_mode(mock_branch_name,
                                                     test_data, tmpdir):
    mock_branch_name.return_value = test_data[0]
    path = tmpdir.join('file.txt')
    path.write(COMMIT_MESSAGE)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'underscore_split', '{ticket}: {commit_msg}')
    assert path.read() == '{expected_ticket}: {message}'.format(
        expected_ticket=test_data[1], message=COMMIT_MESSAGE
    )


@pytest.mark.parametrize('branch_name', (
    'JIRA-1234',
    'JIRA-1234_bar',
    'foo_JIRA-1234_bar',
    'foo-JIRA-1234-bar',
    'foo/JIRA-1234-bar',
    'fooJIRA-1234bar',
    'foo/bar/JIRA-1234',
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_regex_match_mode(mock_branch_name,
                                                branch_name, tmpdir):
    mock_branch_name.return_value = branch_name
    path = tmpdir.join('file.txt')
    path.write(COMMIT_MESSAGE)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket}: {commit_msg}')
    assert path.read() == 'JIRA-1234: {message}'.format(message=COMMIT_MESSAGE)


@pytest.mark.parametrize('test_data', (
    ('JIRA-1234', 'JIRA-1234'),
    ('JIRA-1234-JIRA-239', 'JIRA-1234'),
    ('JIRA-239-JIRA-1234', 'JIRA-239'),
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_multiple_ticket_first_selected(mock_branch_name,
                                                              test_data,
                                                              tmpdir):
    mock_branch_name.return_value = test_data[0]
    path = tmpdir.join('file.txt')
    path.write(COMMIT_MESSAGE)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket}: {commit_msg}')
    assert path.read() == '{expected_ticket}: {message}'.format(
        expected_ticket=test_data[1], message=COMMIT_MESSAGE
    )


@pytest.mark.parametrize('test_data', (
    ('JIRA-1234', 'JIRA-1234'),
    ('JIRA-1234-JIRA-239', 'JIRA-1234, JIRA-239'),
    ('JIRA-239-JIRA-1234', 'JIRA-239, JIRA-1234'),
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_multiple_ticket_all_selected(mock_branch_name,
                                                            test_data, tmpdir):
    mock_branch_name.return_value = test_data[0]
    path = tmpdir.join('file.txt')
    path.write(COMMIT_MESSAGE)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{tickets}: {commit_msg}')
    assert path.read() == '{expected_tickets}: {message}'.format(
        expected_tickets=test_data[1], message=COMMIT_MESSAGE
    )


@pytest.mark.parametrize('msg', (
    "\n",
    "a bogus message\n"
    """A message

With a description\n""",
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_ci_message_with_nl_regex_match_mode(mock_branch_name, msg, tmpdir):
    first_line = msg.split('\n')[0].strip()
    mock_branch_name.return_value = "JIRA-239_mock_branch"
    path = tmpdir.join('file.txt')
    path.write(msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{commit_msg} - {ticket}')
    assert path.read().split('\n')[0] == "{first_line} - {ticket}".format(first_line=first_line, ticket="JIRA-239")


@pytest.mark.parametrize('msg', (
    """A descriptive header

A descriptive body.

Issue: 2397""",
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_no_modification_if_ticket_in_body(mock_branch_name, msg, tmpdir):
    mock_branch_name.return_value = "team_name/2397/a_nice_feature"
    path = tmpdir.join('file.txt')
    path.write(msg)
    update_commit_message(six.text_type(path), r'\d{4,}',
                          'regex_match', '{commit_msg}\n\nIssue: {ticket}')
    assert path.read() == msg


@pytest.mark.parametrize('msg', (
    """fixup! A descriptive header

A descriptive body.""",
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_no_modification_if_commit_is_a_fixup(mock_branch_name, msg, tmpdir):
    mock_branch_name.return_value = "team_name/2397/a_nice_feature"
    path = tmpdir.join('file.txt')
    path.write(msg)
    update_commit_message(six.text_type(path), r'\d{4,}',
                          'regex_match', '{commit_msg}\n\nIssue: {ticket}')
    assert path.read() == msg


@pytest.mark.parametrize('test_data', (
    ('fix(FE): some message', 'SP-1234', 'fix(FE): SP-1234 some message'),
    ('feat(UI): awesome feature', 'SP-5678', 'feat(UI): SP-5678 awesome feature'),
    ('chore(DEPS): update dependencies', 'SP-9012', 'chore(DEPS): SP-9012 update dependencies'),
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_conventional_commit_structure(mock_branch_name, test_data, tmpdir):
    commit_msg, ticket, expected_msg = test_data
    mock_branch_name.return_value = "feature/{0}/some-branch-name".format(ticket)
    path = tmpdir.join('file.txt')
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    assert path.read() == expected_msg


@pytest.mark.parametrize('test_data', (
    ('FiX(cp): some message', 'SP-1234', 'fix(CP): SP-1234 some message'),
    ('FEAT(ui): awesome feature', 'SP-5678', 'feat(UI): SP-5678 awesome feature'),
    ('ChOrE(deps): update dependencies', 'SP-9012', 'chore(DEPS): SP-9012 update dependencies'),
))
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_case_normalization(mock_branch_name, test_data, tmpdir):
    commit_msg, ticket, expected_msg = test_data
    mock_branch_name.return_value = "feature/{0}/some-branch-name".format(ticket)
    path = tmpdir.join('file.txt')
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    assert path.read() == expected_msg


@pytest.mark.parametrize('invalid_type', (
    'invalid',
    'unknown',
    'notallowed',
))
@mock.patch(TESTING_MODULE + '.sys.stderr.write')
@mock.patch(TESTING_MODULE + '.sys.exit')
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_invalid_type(mock_branch_name, mock_exit, mock_stderr_write, invalid_type, tmpdir):
    mock_branch_name.return_value = "feature/SP-1234/some-branch-name"
    path = tmpdir.join('file.txt')
    commit_msg = f"{invalid_type}(CP): some message"
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    mock_exit.assert_called_once_with(1)
    mock_stderr_write.assert_any_call(f"WRONG TYPE DETECTED: Invalid commit type '{invalid_type}'. Allowed types are: {', '.join(ALLOWED_TYPES)}\n")


@pytest.mark.parametrize('test_data', (
    ('fet', 'feat'),
    ('fixx', 'fix'),
    ('enhh', 'enh'),
))
@mock.patch(TESTING_MODULE + '.sys.stderr.write')
@mock.patch(TESTING_MODULE + '.sys.exit')
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_type_suggestion(mock_branch_name, mock_exit, mock_stderr_write, test_data, tmpdir):
    invalid_type, suggested_type = test_data
    mock_branch_name.return_value = "feature/SP-1234/some-branch-name"
    path = tmpdir.join('file.txt')
    commit_msg = f"{invalid_type}(CP): some message"
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    mock_exit.assert_called_once_with(1)
    mock_stderr_write.assert_any_call(f"Do you mean `{suggested_type}` instead of `{invalid_type}`?\n")
    mock_stderr_write.assert_any_call(f"WRONG TYPE DETECTED: Invalid commit type '{invalid_type}'. Allowed types are: {', '.join(ALLOWED_TYPES)}\n")


@pytest.mark.parametrize('invalid_scope', (
    'INVALID',
    'UNKNOWN',
    'NOTALLOWED',
))
@mock.patch(TESTING_MODULE + '.sys.stderr.write')
@mock.patch(TESTING_MODULE + '.sys.exit')
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_invalid_scope(mock_branch_name, mock_exit, mock_stderr_write, invalid_scope, tmpdir):
    mock_branch_name.return_value = "feature/SP-1234/some-branch-name"
    path = tmpdir.join('file.txt')
    commit_msg = f"fix({invalid_scope}): some message"
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    mock_exit.assert_called_once_with(1)
    mock_stderr_write.assert_any_call(f"WRONG SCOPE DETECTED: Invalid commit scope '{invalid_scope}'. Allowed scopes are: {', '.join(ALLOWED_SCOPES)}\n")


@pytest.mark.parametrize('test_data', (
    ('CPPP', 'CP'),
    ('UII', 'UI'),
    ('DOCC', 'DOC'),
))
@mock.patch(TESTING_MODULE + '.sys.stderr.write')
@mock.patch(TESTING_MODULE + '.sys.exit')
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_scope_suggestion(mock_branch_name, mock_exit, mock_stderr_write, test_data, tmpdir):
    invalid_scope, suggested_scope = test_data
    mock_branch_name.return_value = "feature/SP-1234/some-branch-name"
    path = tmpdir.join('file.txt')
    commit_msg = f"fix({invalid_scope}): some message"
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    mock_exit.assert_called_once_with(1)
    mock_stderr_write.assert_any_call(f"Do you mean `{suggested_scope}` instead of `{invalid_scope}`?\n")
    mock_stderr_write.assert_any_call(f"WRONG SCOPE DETECTED: Invalid commit scope '{invalid_scope}'. Allowed scopes are: {', '.join(ALLOWED_SCOPES)}\n")


@mock.patch(TESTING_MODULE + '.sys.stderr.write')
@mock.patch(TESTING_MODULE + '.sys.exit')
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_invalid_format(mock_branch_name, mock_exit, mock_stderr_write, tmpdir):
    mock_branch_name.return_value = "feature/SP-1234/some-branch-name"
    path = tmpdir.join('file.txt')
    commit_msg = "invalid format message"
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')
    mock_exit.assert_called_once_with(1)
    mock_stderr_write.assert_any_call("WRONG FORMAT DETECTED: Commit message must follow the format 'type(scope): message'\n")
    mock_stderr_write.assert_any_call(f"Allowed types: {', '.join(ALLOWED_TYPES)}\n")
    mock_stderr_write.assert_any_call(f"Allowed scopes: {', '.join(ALLOWED_SCOPES)}\n")


@pytest.mark.parametrize('test_data', (
    (('fet', 'feat'), ('CPPP', 'CP')),
    (('fixx', 'fix'), ('UII', 'UI')),
    (('enhh', 'enh'), ('DOCC', 'DOC')),
))
@mock.patch(TESTING_MODULE + '.sys.stderr.write')
@mock.patch(TESTING_MODULE + '.sys.exit')
@mock.patch(TESTING_MODULE + '.get_branch_name')
def test_update_commit_message_both_invalid(mock_branch_name, mock_exit, mock_stderr_write, test_data, tmpdir):
    (invalid_type, suggested_type), (invalid_scope, suggested_scope) = test_data
    mock_branch_name.return_value = "feature/SP-1234/some-branch-name"
    path = tmpdir.join('file.txt')
    commit_msg = f"{invalid_type}({invalid_scope}): some message"
    path.write(commit_msg)
    update_commit_message(six.text_type(path), r'[A-Z]+-\d+',
                          'regex_match', '{ticket} {commit_msg}')

    # Check that sys.exit was called once with code 1
    mock_exit.assert_called_once_with(1)

    # Check that all error messages and suggestions were displayed
    mock_stderr_write.assert_any_call(f"Do you mean `{suggested_type}` instead of `{invalid_type}`?\n")
    mock_stderr_write.assert_any_call(f"WRONG TYPE DETECTED: Invalid commit type '{invalid_type}'. Allowed types are: {', '.join(ALLOWED_TYPES)}\n")
    mock_stderr_write.assert_any_call(f"Do you mean `{suggested_scope}` instead of `{invalid_scope}`?\n")
    mock_stderr_write.assert_any_call(f"WRONG SCOPE DETECTED: Invalid commit scope '{invalid_scope}'. Allowed scopes are: {', '.join(ALLOWED_SCOPES)}\n")


def test_find_closest_match():
    # Test with types (lowercase)
    assert find_closest_match('fet', ALLOWED_TYPES) == 'feat'
    assert find_closest_match('fixx', ALLOWED_TYPES) == 'fix'
    assert find_closest_match('enhh', ALLOWED_TYPES) == 'enh'

    # Test with scopes (uppercase)
    assert find_closest_match('CP', ALLOWED_SCOPES) == 'CP'
    assert find_closest_match('CPPP', ALLOWED_SCOPES) == 'CP'
    assert find_closest_match('UII', ALLOWED_SCOPES) == 'UI'

    # Test with no good match
    assert find_closest_match('zzzzz', ALLOWED_TYPES) is None
    assert find_closest_match('ZZZZZ', ALLOWED_SCOPES) is None

    # Test with empty input
    assert find_closest_match('', ALLOWED_TYPES) is None
    assert find_closest_match(None, ALLOWED_TYPES) is None


@mock.patch(TESTING_MODULE + '.subprocess')
def test_get_branch_name(mock_subprocess):
    get_branch_name()
    mock_subprocess.check_output.assert_called_once_with(
        [
            'git',
            'rev-parse',
            '--abbrev-ref',
            'HEAD',
        ],
    )


@mock.patch(TESTING_MODULE + '.argparse')
@mock.patch(TESTING_MODULE + '.update_commit_message')
def test_main(mock_update_commit_message, mock_argparse):
    mock_args = mock.Mock()
    mock_args.filenames = ['foo.txt']
    mock_args.regex = None
    mock_args.format = None
    mock_args.mode = 'underscore_split'
    mock_argparse.ArgumentParser.return_value.parse_args.return_value = mock_args
    main()
    mock_update_commit_message.assert_called_once_with('foo.txt', r'[A-Z]+-\d+',
                                                       'underscore_split',
                                                       '{ticket} {commit_msg}')
