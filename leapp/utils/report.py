import hashlib
import json

from leapp.reporting import Remediation, create_report_from_error
from leapp.utils.audit import get_messages


def fetch_upgrade_report_messages(context_id):
    """
    :param context_id: ID to identify the needed messages
    :type context_id: str
    :return: All upgrade messages of type "Report" withing the given context
    """
    report_msgs = get_messages(names=['Report', 'ErrorModel'], context=context_id) or []

    messages = []
    for message in report_msgs:
        data = message['message']['data']

        # We need to be able to uniquely identify each message so we compute
        # a hash of: context UUID, message ID in the database and hash of the
        # data section of the message itself
        sha256 = hashlib.sha256()
        sha256.update(message['message']['hash'].encode('utf-8'))
        sha256.update(message['context'].encode('utf-8'))
        sha256.update(str(message['id']).encode('utf-8'))

        envelope = {
            'timeStamp': message['stamp'],
            'hostname': message['hostname'],
            'actor': message['actor'],
            'id': sha256.hexdigest()
        }
        data_json = json.loads(data)
        report = json.loads(data_json.get('report', "{}"))
        if not report:
            # transform Error message to Report message
            report = create_report_from_error(data_json)
        report.update(envelope)
        messages.append(report)

    return messages


def generate_report_file(messages_to_report, context, path):
    if path.endswith(".txt"):
        with open(path, 'w') as f:
            for message in messages_to_report:
                is_inhibitor = 'inhibitor' in message.get('flags', [])
                f.write('Risk Factor: {}{}\n'.format(message['severity'], ' (inhibitor)' if is_inhibitor else ''))
                f.write('Title: {}\n'.format(message['title']))
                f.write('Summary: {}\n'.format(message['summary']))
                remediation = Remediation.from_dict(message.get('detail', {}))
                if remediation:
                    f.write('Remediation: {}\n'.format(remediation))
                f.write('-' * 40 + '\n')
    elif path.endswith(".json"):
        with open(path, 'w') as f:
            json.dump({'entries': messages_to_report, 'leapp_run_id': context}, f, indent=2)
