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

import glance.openstack.common.log as logging

CONFIG = ConfigParser.SafeConfigParser()

RULES = []

LOG = logging.getLogger(__name__)

class PropertyRules(object):

    def __init__(self, roles):
        self.roles = roles
        self._load_config_for_env('/etc/glance/glance-properties')

    def _load_config_for_env(self, env):
        conf_file = env + ".conf"
        CONFIG.read(conf_file)

        properties = CONFIG.sections()
        for property_exp in properties:
            property_dict = {}
            try:

                property_dict['C'] = CONFIG.get(property_exp, 'C').split(',')
                property_dict['R'] = CONFIG.get(property_exp, 'R').split(',')
                property_dict['U'] = CONFIG.get(property_exp, 'U').split(',')
                property_dict['D'] = CONFIG.get(property_exp, 'D').split(',')
                RULES.append({property_exp: property_dict})
            except ConfigParser.NoOptionError as e:
                raise e

    def check_property_rules(self, property_name, action):
        LOG.info(str(property_name))

        if not RULES:
            return True

        for rule in RULES:
            rule_exp = rule.keys()[0]
            LOG.info(rule_exp)
            rule = rule[rule_exp]
            compiled_rule = re.compile(rule_exp)
            if compiled_rule.search(str(property_name)):
                for role in self.roles:
                    msg = ("role %s checking against rule role %s" %(role,
                            rule[action]))
                    LOG.info(msg)
                    if role in rule[action]:
                        LOG.info("returning tru")
                        return True
        LOG.info("returning false")
        return False
