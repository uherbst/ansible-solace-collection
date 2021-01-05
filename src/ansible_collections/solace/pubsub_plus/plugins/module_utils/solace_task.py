# Copyright (c) 2020, Solace Corporation, Ricardo Gomez-Ulmke, <ricardo.gomez-ulmke@solace.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import ansible_collections.solace.pubsub_plus.plugins.module_utils.solace_sys as solace_sys
from ansible_collections.solace.pubsub_plus.plugins.module_utils.solace_utils import SolaceUtils
from ansible_collections.solace.pubsub_plus.plugins.module_utils.solace_error import SolaceInternalError, SolaceInternalErrorAbstractMethod, SolaceApiError, SolaceParamsValidationError
from ansible_collections.solace.pubsub_plus.plugins.module_utils.solace_task_config import SolaceTaskConfig, SolaceTaskBrokerConfig
from ansible_collections.solace.pubsub_plus.plugins.module_utils.solace_api import SolaceApi
from ansible.module_utils.basic import AnsibleModule
import logging

SOLACE_TASK_HAS_IMPORT_ERROR = False
SOLACE_TASK_ERR_TRACEBACK = None
import traceback
try:
    import requests
except ImportError:
    SOLACE_TASK_HAS_IMPORT_ERROR = True
    SOLACE_TASK_ERR_TRACEBACK = traceback.format_exc()

if not SOLACE_TASK_HAS_IMPORT_ERROR:
    class BearerAuth(requests.auth.AuthBase):
        def __init__(self, token):
            self.token = token

        def __call__(self, r):
            r.headers["authorization"] = "Bearer " + self.token
            return r


class SolaceTask(object):

    def __init__(self, module: AnsibleModule):
        SolaceUtils.module_fail_on_import_error(module, SOLACE_TASK_HAS_IMPORT_ERROR, SOLACE_TASK_ERR_TRACEBACK)
        self.module = module
        self.changed = False
        return

    def get_module(self) -> AnsibleModule:
        return self.module

    def get_config(self) -> SolaceTaskConfig:
        raise SolaceInternalErrorAbstractMethod()

    def create_result(self, rc=0, changed=False) -> dict:
        return SolaceUtils.create_result(rc, changed)

    def validate_params(self):
        return

    def do_task(self):
        # return: msg(dict) and result(dict)
        raise SolaceInternalErrorAbstractMethod()

    def execute(self):
        # safe call to do_task(), exits / fails the module
        try:
            msg, result = self.do_task()
            self.module.exit_json(msg=msg, **result)
        except SolaceApiError as e:
            result = self.create_result(rc=1, changed=self.changed)
            self.module.exit_json(msg=e.get_ansible_msg(), **result)
        except SolaceInternalError as e:    
            ex = traceback.format_exc()
            ex_msg_list = e.to_list()
            msg = ["Pls raise an issue including the full traceback. (hint: use -vvv)"] + ex_msg_list + ex.split('\n')
            result = self.create_result(rc=1, changed=self.changed)
            self.module.exit_json(msg=msg, **result)
        except SolaceParamsValidationError as e:
            msg = ["module arg validation failed", str(e)]
            result = self.create_result(rc=1, changed=False)
            self.module.exit_json(msg=msg, **result)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # logging.debug("Request Error: %s", str(e))
            result = self.create_result(rc=1, changed=self.changed)
            self.module.exit_json(msg=str(e), **result) 
        except Exception as e:
            # TODO: testing
            import logging
            logging.debug(f"type(Exception)={type(e)}")
            ex = traceback.format_exc()
            msg = [str(e)] + ex.split('\n')
            result = self.create_result(rc=1, changed=self.changed)
            self.module.exit_json(msg=msg, **result)


class SolaceBrokerTask(SolaceTask):

    def __init__(self, module: AnsibleModule):
        super().__init__(module)
        self.config = SolaceTaskBrokerConfig(module)

    def get_config(self) -> SolaceTaskBrokerConfig:
        return self.config

    def get_sempv2_version_as_float(self) -> float:
        if self.config.sempv2_version is None:
            from ansible_collections.solace.pubsub_plus.plugins.module_utils.solace_sempv2_api import SolaceSempV2Api
            sempv2_api = SolaceSempV2Api(self.module)
            sempv2_version = sempv2_api.get_sempv2_version(self.get_config())
            self.config.set_sempv2_version(sempv2_version)
        try:
            v = float(self.config.sempv2_version)
        except ValueError as e:
            raise ValueError(f"sempv2_version: '{self.config.sempv2_version}' cannot be converted to a float") from e    
        return v


class SolaceBrokerCRUDTask(SolaceBrokerTask):

    def __init__(self, module: AnsibleModule):
        super().__init__(module)

    def get_args(self) -> list:
        raise SolaceInternalErrorAbstractMethod()

    def get_new_settings(self) -> dict:
        s = self.get_module().params['settings']
        if s:
            SolaceUtils.type_conversion(s, self.get_config().is_solace_cloud())
        return s    

    def get_func(self, *args) -> dict:
        raise SolaceInternalErrorAbstractMethod()

    def create_func(self, *args) -> dict:
        raise SolaceInternalErrorAbstractMethod()

    def update_func(self, *args) -> dict:
        raise SolaceInternalErrorAbstractMethod()

    def delete_func(self, *args) -> dict:
        raise SolaceInternalErrorAbstractMethod()

    def do_task(self):
        
        self.validate_params()
        args = self.get_args()
        new_settings = self.get_new_settings()    
        current_settings = self.get_func(*args)
        new_state = self.get_module().params['state']

        # delete if exists
        if new_state =='absent':
            if current_settings is None:
                return None, self.create_result(rc=0, changed=False)
            result = self.create_result(rc=0, changed=True)
            if not self.get_module().check_mode:
                result['response'] = self.delete_func(*args)
            return None, result

        # create if not exist
        if new_state == 'present' and current_settings is None:
            result = self.create_result(rc=0, changed=True)
            if not self.get_module().check_mode:
                args.append(new_settings)
                result['response'] = self.create_func(*args)
            return None, result

        # update if any changes
        if new_state == 'present' and current_settings is not None:
            update_settings = None
            if new_settings is not None:
                update_settings = {k: v for k,v in new_settings.items() if (k in current_settings and v != current_settings[k]) or k not in current_settings}
            if not update_settings:
                return None, self.create_result(rc=0, changed=False)
            if update_settings:
                result = self.create_result(rc=0, changed=True)
                if not self.get_module().check_mode:
                    # sending all settings to update ==> no missing together, required, check necessary
                    args.append(new_settings)
                    result['response'] = self.update_func(*args)
            return None, result
        
        # should never get here
        raise SolaceInternalError("unhandled task combination")