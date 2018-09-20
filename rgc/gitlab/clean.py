import gitlab
import json
import re
import rgc.registry
from datetime import datetime
from rgc.registry.api import RegistryApi
from termcolor import colored

class GitlabClean( object ):
    def __init__( self, user, token, gitlab_url, registry_url, retention, exclude ):
       self.user         = user
       self.token        = token
       self.gitlab_url   = gitlab_url
       self.registry_url = registry_url
       self.retention    = retention
       self.exclude      = exclude

    def clean_projects( self ):
        registry = RegistryApi(
            user  = self.user,
            token = self.token
        )

        now = datetime.now()

        print(' -> fetch registry catalog...')
        images = registry.query( self.registry_url + '/v2/_catalog?n=9999', 'get' )["repositories"]

        print( '-> loading all projects..' )
        for project in gitlab.Gitlab( self.gitlab_url, self.token ).projects.list( all=True ):
            if not project.container_registry_enabled:
                print( '-> skipping ' + project.path_with_namespace.lower() )
                continue

            subimages = []
            for image in images:
                if project.path_with_namespace.lower() == image or \
                        image.startswith(project.path_with_namespace.lower() + '/'):
                    subimages.append(image)

            for subimage in subimages:
                print( '-> processing ' + subimage )
                query_tags = registry.query( self.registry_url + '/v2/' + subimage + '/tags/list', 'get' )
                tags = query_tags.get('tags', [])

                if not tags:
                    print( '--> no tags' )
                    continue

                print( '--> ' + str( len( tags ) ) + ' tag(s) found' )
                for tag in tags:
                    if re.match( self.exclude, tag ):
                        print( colored( '--> keeping ' + tag + ' (excluded)', 'green' ) )
                        continue

                    # BUG: Sometimes the 'history' field is not available, usally works on next try
                    tag_info = registry.query( self.registry_url + '/v2/' + subimage + '/manifests/' + tag, 'get' )
                    if not 'history' in tag_info:
                        print( colored( '--> couldn\'t get date info for ' + tag + ' (skipped)', 'yellow' ) )
                        continue

                    created_at = datetime.strptime( json.loads( tag_info['history'][0]['v1Compatibility'] )['created'][:-4], '%Y-%m-%dT%H:%M:%S.%f' )
                    age = now - created_at
                    if age.total_seconds() > ( int( self.retention ) * 60 * 60 * 24 ):
                        print( colored( '--> removing ' + tag + ' (expired)', 'red' ) )
                        digest = registry.query( self.registry_url + '/v2/' + subimage + '/manifests/' + tag, 'head' )['Docker-Content-Digest']
                        registry.query( self.registry_url + '/v2/' + subimage + '/manifests/' + digest, 'delete' )
                    else:
                        print( colored( '--> keeping ' + tag + ' (not expired)', 'green' ) )
