import re
import random
import string

from flask import Flask
from flask import render_template
from gitlab import Gitlab
from base64 import b64decode

import config

app = Flask(__name__)

def get_random_identifier():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(4))

def get_random_identifiers(identifiers, missing_count):
    random_identifiers = []

    while len(random_identifiers) < missing_count:
        x = get_random_identifier()

        if (x not in random_identifiers) and (x not in identifiers):
            random_identifiers.append(x)

    return random_identifiers

@app.route("/<namespace>/<project_name>/<branch>/<path:file_path>")
def collabr(namespace, project_name, branch, file_path):
    git = Gitlab(config.GITLAB_SERVER, token=config.GITLAB_TOKEN)

    project_info = git.getproject(namespace + '/' + project_name)

    file_container = git.getfile(project_id=project_info['id'], file_path=file_path, ref=branch)
    file_content = b64decode(file_container['content'])
    issues = git.getall(git.getprojectissues, project_id=project_info['id'])

    sections = re.findall(r'\\((?:sub)*section|paragraph)\*?(\[\w+\])*{(.*?)}', file_content)
    identifiers = [section[1] for section in sections if section[1] != '']
    missing_count = len(sections) - len(identifiers)
    random_identifiers = get_random_identifiers(identifiers, missing_count)

    return render_template('rcollab.html', project_name=project_name, branch=branch, file_path=file_path, commit_id=file_container['commit_id'], sections=sections, missing_count=missing_count, random_identifiers=random_identifiers)

if __name__ == "__main__":
    app.run(debug=True)
