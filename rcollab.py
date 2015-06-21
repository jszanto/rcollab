import re
import random
import string

from flask import Flask
from flask import render_template
from gitlab import Gitlab
from base64 import b64decode

import config

app = Flask(__name__)

def cleanup_issue(issue, identifier):
    issue['title'] = issue['title'].replace(identifier, '').strip()

    if issue['title'] == '':
        issue['title'] = '-'

    return issue

def get_random_identifier():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(4))

def get_random_identifiers(sections):
    current_identifiers = [section[1] for section in sections if section[1] != '']
    missing_count = len(sections) - len(current_identifiers)

    random_identifiers = []

    while len(random_identifiers) < missing_count:
        x = get_random_identifier()

        if (x not in random_identifiers) and (x not in current_identifiers):
            random_identifiers.append(x)

    return random_identifiers

def get_sections(file_content):
    return re.findall(r'[^%]\\((?:sub)*section|paragraph)\*?(\[\w+\])*{(.*?)}', file_content)

def get_issues(git, project_info):
    issues = git.getall(git.getprojectissues, project_id=project_info['id'])
    return [issue for issue in issues]

@app.route("/<namespace>/<project_name>/<branch>/<path:file_path>")
def collabr(namespace, project_name, branch, file_path):
    git = Gitlab(config.GITLAB_SERVER, token=config.GITLAB_TOKEN)

    project_info = git.getproject(namespace + '/' + project_name)
    file_container = git.getfile(project_id=project_info['id'], file_path=file_path, ref=branch)
    file_content = b64decode(file_container['content'])

    sections = get_sections(file_content)
    issues = get_issues(git, project_info)
    random_identifiers = get_random_identifiers(sections)

    sections_extended = []

    for section in sections:
        section_issues = [cleanup_issue(issue, section[1]) for issue in issues if (section[1] != '' and section[1] in issue['title'])]
        section_issues.sort(key = lambda issue: issue['iid'])
        sections_extended.append((section[0], section[1], section[2], section_issues, len([x for x in section_issues if x['state'] == 'opened']) == 0))

    return render_template('rcollab.html', branch=branch, file_path=file_path, project_info=project_info, commit_id=file_container['commit_id'], sections_extended=sections_extended, missing_count=len(random_identifiers), random_identifiers=random_identifiers)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=38711)
