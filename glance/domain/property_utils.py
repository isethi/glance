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

import glance.openstack.common.log as logging

CONFIG = ConfigParser.SafeConfigParser()

LOG = logging.getLogger(__name__)
property_opts = [
    cfg.StrOpt('property_protection_file', default='property-protections.conf',
               help=_('The location of the property policy file.')),
]

CONF = cfg.CONF
CONF.register_opts(property_opts)


class PropertyRules(object):

    def __init__(self):
        LOG.info(str(CONF.property_protection_file))
        self._load_config_for_env(CONF.property_protection_file)

    def _load_config_for_env(self, env):
        conf_file = CONF.find_file(env)
        CONFIG.read(conf_file)

        self.rules = []
        properties = CONFIG.sections()
        for property_exp in properties:
            property_dict = {}
            try:

                property_dict['create'] = CONFIG.get(property_exp, 'create').split(',')
                property_dict['read'] = CONFIG.get(property_exp, 'read').split(',')
                property_dict['update'] = CONFIG.get(property_exp, 'update').split(',')
                property_dict['delete'] = CONFIG.get(property_exp, 'delete').split(',')
                self.rules.append({property_exp: property_dict})
            except ConfigParser.NoOptionError as e:
                raise e
            LOG.info(str(self.rules))

    def check_property_rules(self, property_name, action, roles):
        if not self.rules:
            return True

        for rule in self.rules:
            rule_exp = rule.keys()[0]
            LOG.info(rule_exp)
            rule = rule[rule_exp]
            compiled_rule = re.compile(rule_exp)
            if compiled_rule.search(str(property_name)):
                for role in roles:
                    msg = ("%s:%s role %s checking against rule role %s" %(property_name,
                            action, role, rule[action]))
                    LOG.info(msg)
                    if role in rule[action]:
                        LOG.info("returning tru")
                        return True
        LOG.info("returning false")
        return False
