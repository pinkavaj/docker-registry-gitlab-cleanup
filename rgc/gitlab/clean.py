import gitlab
import json
import re
import requests
from urllib.parse import quote
from datetime import datetime
from termcolor import colored


class GitlabClean(object):
    def __init__(self, user, token, gitlab_url, retention, exclude):
        self.user = user
        self.token = token
        self.auth_headers = {'PRIVATE-TOKEN': token}
        self.gitlab_url = gitlab_url
        self.exclude = exclude
        self.api_url = '%s/api/v4' % gitlab_url
        self.retention_limit = \
            datetime.utcnow().timestamp() - int(retention) * 24 * 60 * 60

    def clean_projects(self):
        gl = gitlab.Gitlab(self.gitlab_url, self.token, per_page=100)
        print('Loading all projects ...')
        for project in gl.projects.list(all=True):
            project_path = project.path_with_namespace
            project_path_q = quote(project_path, safe='')
            if not project.container_registry_enabled:
                print(colored('skipping project ' + project_path, 'yellow'))
                continue
            print(colored('# project ' + project_path))

            url = '%s/projects/%s/registry/repositories' % (
                self.api_url, project_path_q
            )
            for registry in self.get_list(url):
                print('## registry %s' % registry['name'])
                registry_id = registry['id']
                url = '%s/projects/%s/registry/repositories/%d/tags' % (
                    self.api_url, project_path_q, registry_id
                )
                for tag in self.get_list(url):
                    tag_name = tag['name']
                    if re.match(self.exclude, tag_name):
                        print(colored(f'keeping (excluded) {tag_name}', 'green'))
                        continue
                    url = '%s/projects/%s/registry/repositories/%d/tags/%s' % (
                        self.api_url, project_path_q, registry_id, tag_name
                    )
                    res = requests.get(url, headers=self.auth_headers)
                    if res.status_code == 404:
                        print(
                            colored(
                                f'skipping (unaccesible) {tag_name}', 'yellow'
                            )
                        )
                        continue
                    if res.status_code != 200:
                        res.raise_for_status()
                    created_at = res.json()['created_at']
                    self.process_tag(
                        project_path_q, registry_id, tag_name, created_at
                    )

    def get_list(self, url):
        params = {'per_page': 100}
        while url:
            res = requests.get(url, headers=self.auth_headers, params=params)
            links = res.headers['Link'].split(',')
            url = None
            for link in links:
                link = link.strip()
                url_next, rel = link.split(';')
                if rel.strip() != 'rel="next"':
                    continue
                url = url_next.strip()[1:][:-1]
                break
            if res.status_code != 200:
                res.raise_for_status()
            for item in res.json():
                yield item

    def process_tag(self, project_path_q, registry_id, tag_name, created_at):
        created_at_time = datetime.fromisoformat(created_at)
        if created_at_time.timestamp() > self.retention_limit:
            print(colored(f'keeping (not expired) {tag_name}', 'green'))
            return
        print(colored(f'removing {tag_name} (expired)', 'red'))
        url = '%s/projects/%s/registry/repositories/%d/tags/%s' % (
            self.api_url, project_path_q, registry_id, tag_name
        )
        res = requests.delete(url, headers=self.auth_headers)
        if res.status_code != 200:
            res.raise_for_status()
