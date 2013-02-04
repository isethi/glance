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

from webob import Response
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

    def _check_can_access_image_members(self, context):
        if context.owner is None and not context.is_admin:
            raise webob.exc.HTTPUnauthorized(_("No authenticated user"))

    def _format_image_member(self, image_member):
        image_member_view = {}
        attributes = ['member_id', 'image_id', 'created_at', 'updated_at']
        for key in attributes:
            image_member_view[key] = getattr(image_member, key)
        return image_member_view

    @utils.mutating
    def create(self, req, image_id, member_id):
        """
        Adds a membership to the image.
        :param req: the Request object coming from the wsgi layer
        :param image_id: the image identifier
        :param member_id: the member identifier
        :retval The response body is a mapping of the following form::

            {'member_id': <MEMBER>,
             'image_id': <IMAGE>,
             'created_at': ..,
             'updated_at': ..}

        """
        self._check_can_access_image_members(req.context)
        image_repo = self.gateway.get_repo(req.context)
        image_member_factory = self.gateway\
                                   .get_image_member_factory(req.context)
        try:
            image = image_repo.get(image_id)
            image_membership_repo = self.gateway\
                                        .get_membership_repo(req.context,
                                                             image)
            new_member = image_member_factory.new_image_membership(image_id,
                                                               member_id)
            member = image_membership_repo.add(new_member)
            self._update_store_acls(req, image)
            return self._format_image_member(member)
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))

    @utils.mutating
    def index(self, req, image_id):
        """
        Return a list of dictionaries indicating the members of the
        image, i.e., those tenants the image is shared with.

        :param req: the Request object coming from the wsgi layer
        :param image_id: The image identifier
        :retval The response body is a mapping of the following form::

            {'members': [
                {'member_id': <MEMBER>,
                 'image_id': <IMAGE>,
                 'created_at': ..,
                 'updated_at': ..}, ..
            ]}
        """
        image_repo = self.gateway.get_repo(req.context)
        try:
            image = image_repo.get(image_id)
            member_repo = self.gateway.get_membership_repo(req.context,
                                                           image=image)
            members = []
            for member in member_repo.list_members():
                members.append(self._format_image_member(member))
            return dict(members=members)
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))

    @utils.mutating
    def delete(self, req, image_id, member_id):
        """
        Removes a membership from the image.
        """
        self._check_can_access_image_members(req.context)

        image_repo = self.gateway.get_repo(req.context)
        try:
            image = image_repo.get(image_id)
            member_repo = self.gateway.get_membership_repo(req.context, image=image)
            member = member_repo.list_members(member_id=member_id)
            if len(member) == 0:
                raise exception.NotFound()
            member_repo.remove(member[0])
            self._update_store_acls(req, image)
            return Response(body='', status=200)
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))

    def index_shared_images(self, req, member_id):
        """
        Retrieves list of image memberships for the given member.

        :param req: the Request object coming from the wsgi layer
        :param member_id: the member identifier
        :retval The response body is a mapping of the following form::

            {'shared_images': [
                {'image_id': <IMAGE>},
                ...
            ]}
        """
        try:
            tenant = glance.domain.Tenant(member_id)
            image_membership_repo = self.gateway.get_membership_repo(
                                        req.context, tenant=tenant)
            image_repo = self.gateway.get_repo(req.context)
            shared_images = []
            for image in image_membership_repo.list_images(image_repo):
                shared_images.append({'image_id': image.image_id})
        except exception.NotFound as e:
            raise webob.exc.HTTPNotFound(explanation=unicode(e))
        except exception.Forbidden as e:
            raise webob.exc.HTTPForbidden(explanation=unicode(e))
        return dict(shared_images=shared_images)

    def _update_store_acls(self, req, image):
        location_uri = image.location
        public = image.visibility == 'public'
        member_repo = self.gateway.get_membership_repo(req.context, image=image)
        if location_uri:
            try:
                read_tenants = []
                write_tenants = []
                members = member_repo.list_members()
                if members:
                    for member in members:
                        read_tenants.append(member.member_id)
                glance.store.set_acls(req.context, location_uri, public=public,
                                      read_tenants=read_tenants,
                                      write_tenants=write_tenants)
            except exception.UnknownScheme:
                msg = _("Store for image_id not found: %s") % image_id
                raise webob.exc.HTTPBadRequest(explanation=msg,
                                               request=req,
                                               content_type='text/plain')


def create_resource():
    """Image Members resource factory method"""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    controller = ImageMembersController()
    return wsgi.Resource(controller, deserializer, serializer)
