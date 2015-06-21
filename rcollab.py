import re
import random
import string

from time import strptime, strftime
from flask import Flask, render_template, request, Response
from gitlab import Gitlab
from base64 import b64decode

import config

app = Flask(__name__)

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
    
    result = {}

    for issue in issues:
        x = re.match('(\[\w+\]) (.*)', issue['title'])

        if x != None:
            issue['title'] = x.group(2)

            if issue['milestone'] != None:
                if issue['milestone']['due_date'] != None:
                    due_date = strptime(issue['milestone']['due_date'], '%Y-%m-%d')
                    issue['milestone']['due_date'] = strftime('%d-%m-%Y', due_date)

            result.setdefault(x.group(1), []).append(issue)
            result[x.group(1)].sort(key = lambda issue: issue['iid'])

    return result

def authenticate():
    return Response('...', 401, {'WWW-Authenticate': 'Basic realm="Login with Gitlab details."'})

def get_header_level(t):
    return ['section', 'subsection', 'subsubsection', 'paragraph', ''].index(t)

@app.route("/<namespace>/<project_name>/<branch>/<path:file_path>")
def collabr(namespace, project_name, branch, file_path):
    git = Gitlab(config.GITLAB_SERVER)

    auth = request.authorization

    if not auth:
        return authenticate()

    try:
        git.login(auth.username, auth.password)
    except: # should be more specific here
        return authenticate()

    project_info = git.getproject(namespace + '/' + project_name)
    file_container = git.getfile(project_id=project_info['id'], file_path=file_path, ref=branch)
    file_content = b64decode(file_container['content'])

    sections = get_sections(file_content)
    issues = get_issues(git, project_info)
    random_identifiers = get_random_identifiers(sections)

    is_parent_done = ('', True)

    for i, section in enumerate(sections):
        section_issues = issues[section[1]] if section[1] in issues else []
        section_coloring = 'success'

        if len([x for x in section_issues if x['state'] == 'opened']) != 0:
            section_coloring = 'danger'

        if get_header_level(section[0]) <= get_header_level(is_parent_done[0]):
            is_parent_done = (section[0], section_coloring == 'success')

        if not is_parent_done[1]:
            if section_coloring != 'danger':
                section_coloring = 'warning'

        sections[i] = (section[0], section[1], section[2], section_issues, section_coloring)

    return render_template('rcollab.html', branch=branch, file_path=file_path, project_info=project_info, commit_id=file_container['commit_id'], sections=sections, missing_count=len(random_identifiers), random_identifiers=random_identifiers)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=38711)
