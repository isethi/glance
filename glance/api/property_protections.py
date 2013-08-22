# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Copyright 2013 Rackspace
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

from glance.common import exception
from glance.common import property_utils
import glance.domain.proxy


class ProtectedImageRepoProxy(glance.domain.proxy.Repo):
    def __init__(self, image_repo, context):
        self.context = context
        self.image_repo = image_repo
        proxy_kwargs = {'context': self.context}
        super(ProtectedImageRepoProxy, self).__init__(
                image_repo, item_proxy_class=ProtectedImageProxy,
                item_proxy_kwargs=proxy_kwargs)

    def get(self, image_id):
        return ProtectedImageProxy(self.image_repo.get(image_id),
                                   self.context, 'read')

    def list(self, *args, **kwargs):
        images = self.image_repo.list(*args, **kwargs)
        return [ProtectedImageProxy(image, self.context, 'read')
                for image in images]

    def add(self, image):
        self.image_repo.add(ProtectedImageProxy(image, self.context, 'create'))


class ProtectedImageProxy(glance.domain.proxy.Image):

    def __init__(self, image, context, operation):
        self.image = image
        self.context = context
        self.roles = self.context.roles
        self.protect_properties = property_utils.PropertyRules()
        if operation not in ['read', 'create']:
            # image class needs to be created or read before updating it or
            # deleting it
            msg = _("Image object needs to be created/read before editing it")
            raise exception.Forbidden(msg)

        self.image.extra_properties = ExtraPropertiesProxy(
                                            self.roles,
                                            self.image.extra_properties,
                                            operation)
        super(ProtectedImageProxy, self).__init__(self.image)


class ExtraPropertiesProxy(glance.domain.ExtraProperties):

    def __init__(self, roles, extra_props, operation):
        self.roles = roles
        self.protect_properties = property_utils.PropertyRules()
        extra_properties = {}
        for key in extra_props.keys():
            if self.protect_properties.check_property_rules(key, operation,
                                                            self.roles):
                extra_properties[key] = extra_props[key]
        super(ExtraPropertiesProxy, self).__init__(extra_properties)

    def __getitem__(self, key):
        if self.protect_properties.check_property_rules(key, 'read',
                                                        self.roles):
            return dict.__getitem__(self, key)
        else:
            raise KeyError

    def __setitem__(self, key, value):
        try:
            if self.__getitem__(key):
                if self.protect_properties.check_property_rules(key, 'update',
                                                                self.roles):
                    return dict.__setitem__(self, key, value)
        except KeyError:
            if self.protect_properties.check_property_rules(key, 'create',
                                                            self.roles):
                return dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        if self.protect_properties.check_property_rules(key, 'delete',
                                                        self.roles):
            return dict.__delitem__(self, key)
