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

import ConfigParser
import re

from oslo.config import cfg

CONFIG = ConfigParser.SafeConfigParser()

property_opts = [
    cfg.StrOpt('property_protection_file',
               default='property-protections.conf',
               help=_('The location of the property protection file.')),
]

CONF = cfg.CONF
CONF.register_opts(property_opts)


class PropertyRules(object):

    def __init__(self):
        conf_file = CONF.find_file(CONF.property_protection_file)
        CONFIG.read(conf_file)
        self.rules = {}
        properties = CONFIG.sections()
        for property_exp in properties:
            property_dict = {}
            try:
                create_roles = CONFIG.get(property_exp, 'create')
                read_roles = CONFIG.get(property_exp, 'read')
                update_roles = CONFIG.get(property_exp, 'update')
                delete_roles = CONFIG.get(property_exp, 'delete')

                property_dict['create'] = create_roles.split(',')
                property_dict['read'] = read_roles.split(',')
                property_dict['update'] = update_roles.split(',')
                property_dict['delete'] = delete_roles.split(',')
                self.rules[property_exp] = property_dict
            except ConfigParser.NoOptionError as e:
                raise

    def check_property_rules(self, property_name, action, roles):
        if not self.rules:
            return True

        for rule_exp, rule in self.rules.items():
            compiled_rule = re.compile(rule_exp)
            if compiled_rule.search(str(property_name)):
                if set(roles).intersection(set(rule[action])):
                    return True
        return False
