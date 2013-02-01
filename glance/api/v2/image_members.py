# Copyright 2013 OpenStack, LLC
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

import webob.exc

from glance.api import policy
from glance.common import exception
from glance.common import utils
from glance.common import wsgi
import glance.db
import glance.domain
import glance.gateway
import glance.notifier
import glance.store


class ImageMembersController(object):
    def __init__(self, db_api=None, policy_enforcer=None, notifier=None,
                 store_api=None):
        self.db_api = db_api or glance.db.get_api()
        self.db_api.setup_db_env()
        self.policy = policy_enforcer or policy.Enforcer()
        self.notifier = notifier or glance.notifier.Notifier()
        self.store_api = store_api or glance.store
        self.gateway = glance.gateway.Gateway(self.db_api, self.store_api,
                                              self.notifier, self.policy)

    @utils.mutating
    def create(self, req, image_id, member_id):
        image_repo = self.gateway.get_repo(req.context)
        image_member_factory = self.gateway.get_image_member_factory(req.context)
        try:
            image = image_repo.get(image_id)
            member_repo = image.get_member_repo(req.context, self.gateway)
            new_member = image_member_factory.new_image_member(image_id,
                                                               member_id)
            member = member_repo.add(new_member)
            return member
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))

    @utils.mutating
    def index(self, req, image_id):
        image_repo = self.gateway.get_repo(req.context)
        try:
            image = image_repo.get(image_id)
            member_repo = image.get_member_repo(req.context, self.gateway)
            return member_repo.list()
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))

    #@utils.mutating
    #def update(self, req, image_id, member_id, status):
    #    image_repo = self.gateway.get_repo(req.context)
    #    try:
    #        image = image_repo.get(image_id)
    #        image_member = image.get_member(member_id)
    #        image_member.update(status)
    #        image_repo.save(image)
    #    except exception.NotFound as e:
    #        raise webob.exc.HTTPNotFound(explanation=unicode(e))
    #    except exception.Forbidden as e:
    #        raise webob.exc.HTTPForbidden(explanation=unicode(e))

    @utils.mutating
    def delete(self, req, image_id, member_id):
        image_repo = self.gateway.get_repo(req.context)
        try:
            image = image_repo.get(image_id)
            member_repo = image.get_member_repo(req.context, self.gateway)
            member = member_repo.get(member_id)
            member_repo.remove(member)
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))


def create_resource():
    """Image Members resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    controller = ImageMembersController()
    return wsgi.Resource(controller, serializer=serializer,
                         deserializer=deserializer)
