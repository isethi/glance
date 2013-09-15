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
import webob.exc

from glance.common import exception
from glance.openstack.common import log as logging

CONFIG = ConfigParser.SafeConfigParser()
LOG = logging.getLogger(__name__)

property_opts = [
    cfg.StrOpt('property_protection_file',
               default=None,
               help=_('The location of the property protection file.')),
]

CONF = cfg.CONF
CONF.register_opts(property_opts)


def is_property_protection_enabled():
    if CONF.property_protection_file:
        return True
    return False


class PropertyRules(object):

    def __init__(self, policy_enforcer=None):
        self.rules = {}
        self.policies = []
        self.policy_enforcer = policy_enforcer
        self._load_rules()

    def _load_rules(self):
        try:
            conf_file = CONF.find_file(CONF.property_protection_file)
            CONFIG.read(conf_file)
        except Exception as e:
            msg = _("Couldn't find property protection file %s:%s." %
                    (CONF.property_protection_file, e))
            LOG.error(msg)
            raise webob.exc.HTTPInternalServerError(explanation=msg)

        operations = ['create', 'read', 'update', 'delete']
        properties = CONFIG.sections()
        for property_exp in properties:
            property_dict = {}
            compiled_rule = self._compile_rule(property_exp)

            for operation in operations:
                roles = CONFIG.get(property_exp, operation)
                if roles:
                    if roles.startswith("policy:"):
                        policy_rule = role[len("policy:"):]
                        self._add_policy(str(compiled_rule), operation,
                                         policy_rule)
                        roles = [roles]
                    else:
                        roles = [role.strip() for role in roles.split(',')]
                    property_dict[operation] = roles
                else:
                    property_dict[operation] = []
                    msg = _(('Property protection on operation %s for rule '
                            '%s is not found. No role will be allowed to '
                            'perform this operation.' %
                            (operation, property_exp)))
                    LOG.warn(msg)

            self.rules[compiled_rule] = property_dict

        if self.policies:
            self._load_policies()

    def _compile_rule(self, rule):
        try:
            return re.compile(rule)
        except Exception as e:
            msg = _("Encountered a malformed property protection rule %s:%s."
                    % (rule, e))
            LOG.error(msg)
            raise webob.exc.HTTPInternalServerError(explanation=msg)

    def _add_policy(self, property_exp, action, rule):
        """ Add policy rules to the policy enforcer.
        For example, if property-protections.conf has a config:
        [prop_a]
        create = policy:glance_creator
        then the corresponding policy rule would be:
        "prop_a:create": "rule:glance_creator"
        where glance_creator is defined in policy.json. For example:
        "glance:creator": "role:admin or role:glance_create_user"
        """
        rule_name = "\"%s:%s\"" % (property_exp, action)
        property_rule = ": \"%s\"" % (rule)
        policy_rule = rule_name + property_rule
        self.policies.append(policy_rule)

    def _load_policies(self):
        LOG.info("Reloading policy rules for property protection")
        policy_dict = "{" + ",".join(self.policies) + "}"
        self.policy_enforcer.load_rules(policy_dict)

    def _check_policy(self, property_exp, action, context):
        try:
            self.target = ":".join([property_exp, action])
            self.policy_enforcer.enforce(context, self.target, {})
        except exception.Forbidden:
            return False
        return True

    def check_property_rules(self, property_name, action, context):
        roles = context.roles
        if not self.rules:
            return True

        if action not in ['create', 'read', 'update', 'delete']:
            return False

        for rule_exp, rule in self.rules.items():
            if rule_exp.search(str(property_name)):
                rule_roles = rule.get(action)
                if rule_roles:
                    if rule_roles[0].startswith("policy:"):
                        return self._check_policy(str(rule_exp), action,
                                                  context)
                if set(roles).intersection(set(rule_roles)):
                    return True
        return False
