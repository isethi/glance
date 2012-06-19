# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

import webob.exc

from glance.common import exception
from glance.common import utils
from glance.common import wsgi
import glance.db
from glance.openstack.common import cfg
import glance.schema


CONF = cfg.CONF


class Controller(object):
    def __init__(self, db=None):
        self.db_api = db or glance.db.get_api()
        self.db_api.configure_db()

    def index(self, req, image_id, marker=None, limit=None,
              sort_key='created_at', sort_dir='desc'):
        #NOTE(bcwaldon): call image_get to ensure user has permission
        self.db_api.image_get(req.context, image_id)

        if limit is None:
            limit = CONF.limit_param_default
        limit = min(CONF.api_limit_max, limit)

        try:
            members = self.db_api.image_member_get_all(req.context,
                                                       image_id=image_id,
                                                       marker=marker,
                                                       limit=limit,
                                                       sort_key=sort_key,
                                                       sort_dir=sort_dir)
        except exception.InvalidSortKey as e:
            raise webob.exc.HTTPBadRequest(explanation=unicode(e))
        except exception.NotFound as e:
            raise webob.exc.HTTPBadRequest(explanation=unicode(e))

        return {'access_records': members, 'image_id': image_id}

    def show(self, req, image_id, tenant_id):
        members = self.db_api.image_member_find(req.context,
                                                image_id=image_id,
                                                member=tenant_id)
        try:
            return members[0]
        except IndexError:
            raise webob.exc.HTTPNotFound()

    @utils.mutating
    def create(self, req, image_id, access_record):
        #TODO(bcwaldon): Refactor these methods so we don't need to
        # explicitly retrieve a session object here
        session = self.db_api.get_session()
        print "access record=\n"
        print access_record
        try:
            image = self.db_api.image_get(req.context, image_id,
                    session=session)
        except exception.NotFound:
            raise webob.exc.HTTPNotFound()
        except exception.Forbidden:
            # If it's private and doesn't belong to them, don't let on
            # that it exists
            raise webob.exc.HTTPNotFound()

        # Image is visible, but authenticated user still may not be able to
        # share it
        if not self.db_api.is_image_sharable(req.context, image):
            msg = _("No permission to share that image")
            raise webob.exc.HTTPForbidden(msg)

        access_record['image_id'] = image_id
        return self.db_api.image_member_create(req.context, access_record)

    @utils.mutating
    def delete(self, req, image_id, tenant_id):
        #TODO(bcwaldon): Refactor these methods so we don't need to explicitly
        # retrieve a session object here
        session = self.db_api.get_session()
        members = self.db_api.image_member_find(req.context,
                                                image_id=image_id,
                                                member=tenant_id,
                                                session=session)
        try:
            member = members[0]
        except IndexError:
            raise webob.exc.HTTPNotFound()

        self.db_api.image_member_delete(req.context, member, session=session)


class RequestDeserializer(wsgi.JSONRequestDeserializer):
    def __init__(self):
        super(RequestDeserializer, self).__init__()
        self.schema = get_schema()

    def create(self, request):
        output = super(RequestDeserializer, self).default(request)
        body = output.pop('body')
        self.schema.validate(body)
        body['member'] = body.pop('tenant_id')
        output['access_record'] = body
        return output

    def _validate_limit(self, limit):
        try:
            limit = int(limit)
        except ValueError:
            msg = _("limit param must be an integer")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        if limit < 0:
            msg = _("limit param must be positive")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        return limit

    def _validate_sort_dir(self, sort_dir):
        if sort_dir not in ['asc', 'desc']:
            msg = _('Invalid sort direction: %s' % sort_dir)
            raise webob.exc.HTTPBadRequest(explanation=msg)

        return sort_dir

    def _validate_marker(self, marker):
        try:
            marker = int(marker)
        except ValueError:
            msg = _("marker param must be an integer")
            raise webob.exc.HTTPBadRequest(explanation=msg)

        return marker

    def index(self, request, image_id):
        limit = request.params.get('limit', None)
        marker = request.params.get('marker', None)
        sort_dir = request.params.get('sort_dir', 'desc')
        query_params = {
            'image_id': image_id,
            'sort_key': request.params.get('sort_key', 'created_at'),
            'sort_dir': self._validate_sort_dir(sort_dir),
        }

        if marker is not None:
            query_params['marker'] = self._validate_marker(marker)

        if limit is not None:
            query_params['limit'] = self._validate_limit(limit)

        return query_params


class ResponseSerializer(wsgi.JSONResponseSerializer):
    def _get_access_href(self, image_id, tenant_id=None):
        link = '/v2/images/%s/access' % image_id
        if tenant_id:
            link = '%s/%s' % (link, tenant_id)
        return link

    def _format_access(self, access):
        self_link = self._get_access_href(access['image_id'], access['member'])
        return {
                'tenant_id': access['member'],
                'can_share': access['can_share'],
                'self':  self_link,
                'schema': '/v2/schemas/image/access',
                'image': '/v2/images/%s' % access['image_id'],
            }

    def show(self, response, access):
        record = {'access_record': self._format_access(access)}
        response.body = json.dumps(record)

    def index(self, response, result):
        access_records = result['access_records']
        first_link = '/v2/images/%s/access' % result['image_id']
        body = {
            'access_records': [self._format_access(a)
                               for a in access_records],
            'first': first_link,
            'schema': '/v2/schemas/image/accesses',
        }
        response.body = json.dumps(body)

    def create(self, response, access):
        response.status_int = 201
        response.content_type = 'application/json'
        response.location = self._get_access_href(access['image_id'],
                                                  access['member'])
        response.body = json.dumps({'access': self._format_access(access)})

    def delete(self, response, result):
        response.status_int = 204


def get_schema():
    properties = {
        'tenant_id': {
          'type': 'string',
          'description': 'The tenant identifier',
        },
        'can_share': {
          'type': 'boolean',
          'description': 'Ability of tenant to share with others',
          'default': False,
        },
    }
    return glance.schema.Schema('access', properties)


def create_resource():
    """Image access resource factory method"""
    deserializer = RequestDeserializer()
    serializer = ResponseSerializer()
    controller = Controller()
    return wsgi.Resource(controller, deserializer, serializer)
