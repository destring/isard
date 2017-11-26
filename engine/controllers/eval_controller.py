# from engine import app
from math import ceil, floor
from time import sleep
from random import shuffle, randint

from engine.controllers.status import UpdateStatus
from engine.models.hyp import hyp
from engine.services.db import get_user, update_domain_status, get_domains, get_domain, insert_domain, \
    get_domains_id, get_domains_count, get_hypers_info, get_last_hyp_status, get_hyp_hostname_from_id
from engine.services.log import *

# Example of data dict for create domain
DICT_CREATE_WIN7 = {'allowed': {'categories': False,
                                'groups': False,
                                'roles': False,
                                'users': False},
                    'category': 'testing',
                    'create_dict': {'hardware': {'boot_order': ['disk'],
                                                 'disks': [{'file': 'testing/test_users/test1/prova_win7.qcow2',
                                                            'parent': '/vimet/bases/windows_7v3.qcow2'}],
                                                 'graphics': ['default'],
                                                 'interfaces': ['default'],
                                                 'memory': 2500000,
                                                 'vcpus': 2,
                                                 'videos': ['default']},
                                    'origin': '_windows_7_x64_v3'},
                    'description': '',
                    'detail': None,
                    'group': 'test_users',
                    'hypervisors_pools': ['default'],
                    'icon': 'windows',
                    'id': '_test1_prova_win7',
                    'kind': 'desktop',
                    'name': 'prova win7',
                    'os': 'windows',
                    'server': False,
                    'status': 'Creating',
                    'user': 'test1',
                    'xml': None}

DICT_CREATE = {'allowed': {'categories': False,
                           'groups': False,
                           'roles': False,
                           'users': False},
               'category': 'admin',
               'create_dict': {'hardware': {'boot_order': ['disk'],
                                            'disks': [{'file': None,  # replace
                                                       'parent': None  # replace
                                                       }],
                                            'graphics': ['default'],
                                            'interfaces': ['default'],
                                            'memory': 2000000,
                                            'vcpus': 2,
                                            'videos': ['default']},
                               'origin': None  # replace
                               },
               'description': '',
               'detail': None,
               'group': 'eval',
               'hypervisors_pools': ['default'],
               'icon': None,  # replace
               'id': None,  # replace,
               'kind': 'desktop',
               'name': None,  # replace
               'os': None,  # replace
               'server': False,
               'status': 'Creating',
               'user': 'eval',
               'xml': None}


class EvalController(object):
    def __init__(self, id_pool="default", templates=[{'id': "_windows_7_x64_v3", 'weight': 100}]):
        self.user = get_user('eval')
        self.templates = templates  # Define on database for each pool?
        self.id_pool = id_pool
        self.params = {'MAX_DOMAINS': 10,
                       'CREATE_SLEEP_TIME': 1,
                       'STOP_SLEEP_TIME': 1,
                       'START_SLEEP_TIME': 3,
                       'TEMPLATE_MEMORY': 2000}  # in MB, info duplicated on DICT_CREATE but in bytes
        self._init_domains()
        self._init_hyps()

    def _init_hyps(self):
        self.hyps = []
        hyps = get_hypers_info(self.id_pool, pluck=['id', 'hostname', 'info'])
        for h in hyps:
            # TODO: calcule percent as hyp method
            percent = round(self.params.get('TEMPLATE_MEMORY', 2000) * 100 / h['info']['memory_in_MB'], 2)
            hyp_obj = hyp(h['hostname'])
            hyp_obj.id = h['id']
            hyp_obj.percent_ram_template = percent
            self.hyps.append(hyp_obj)

    def _init_domains(self):
        self.num_domains = self._calcule_num_domains()
        self.defined_domains = self._define_domains()

    def _calcule_num_domains(self):
        hyps = get_hypers_info(self.id_pool, pluck=['id', 'info'])
        m = min(hyps, key=lambda x: x['info']['memory_in_MB'])
        min_mem = m['info']['memory_in_MB']
        # TODO: adjust num_domains value.
        num_domains = floor(min_mem / self.params.get('TEMPLATE_MEMORY', 2000)) * (len(hyps) + 10)
        n = min(self.params.get('MAX_DOMAINS', 10), num_domains)
        eval_log.info("Num of max domains for eval: {}".format(n))
        return n

    def _define_domains(self):
        """
        Define how many domains of each template must use for evaluate.
        :param n:
        :return:
        """
        n = self.num_domains
        total_weight = sum([t['weight'] for t in self.templates])
        if total_weight == 100:
            return {t['id']: ceil(n * t['weight'] / 100) for t in self.templates}
        else:
            # Sum of weigths is different from 100, so we balance it.
            w = 100 / len(self.templates)
            return {t['id']: ceil(n * w / 100) for t in self.templates}

    def clear_domains(self):
        """
        Just for testing purposes.
        :return:
        """
        domains = get_domains(self.user["id"])
        for d in domains:
            update_domain_status('Stopped', d['id'])
        return "Okey"

    def create_domains(self):
        """
        Create domains if necessari
        :return:
        """
        data = {}
        total_created_domains = 0
        eval_log.info("CREATE DOMAINS for pool: {}".format(self.id_pool))
        dd = self.defined_domains  # Define number of domains for each template.
        for t in self.templates:
            n_domains = get_domains_count(self.user["id"], origin=t['id'])
            data[t['id']] = pending = dd[t['id']] - n_domains  # number of pending domains to create
            i = n_domains  # index of new domain
            eval_log.debug("Creating {} pending domains from template: {}".format(pending, t['id']))
            total_created_domains += pending
            while (pending > 0):  # Must create more desktops from this template?
                self._create_eval_domain(t['id'], i)
                pending -= 1
                i += 1
                sleep(self.params["CREATE_SLEEP_TIME"])
        return {"total_created_domains": total_created_domains,
                "data": data}

    def stop_domains(self):
        """
        Stop domains if they are started.
        :return:
        """
        domains = get_domains(self.user["id"], status="Started")
        eval_log.info("Stoping {} domains".format(len(domains)))
        for d in domains:
            update_domain_status('Stopping', d['id'])
            sleep(self.params["STOP_SLEEP_TIME"])
        return {"total_stopped_domains": len(domains),
                "data": None}

    def destroy_domains(self):
        """
        Remove all eval domains.
        Must be removed on each defined pool.
        :return:
        """
        ids = get_domains_id(self.user["id"], self.id_pool)
        for a in ids:
            update_domain_status('Deleting', a['id'])

    def start_domains(self):
        domains_id_list = self._get_domains_id_randomized()
        total_domains = len(domains_id_list)
        threshold = floor(total_domains / 2)
        keep_starting = True
        started_domains = 0
        while (len(domains_id_list) and keep_starting):
            upper_limit_random = len(domains_id_list) if len(domains_id_list) < threshold else threshold
            n = randint(1, upper_limit_random)
            eval_log.debug("Starting {} random domains".format(n))
            started_domains += n
            sleep_time = self.params["START_SLEEP_TIME"] * n
            while (n):
                id = domains_id_list.pop()
                update_domain_status('Starting', id)
                n -= 1
            eval_log.debug("Waiting for next start {} seconds".format(sleep_time))
            sleep(sleep_time)
            keep_starting = self._evaluate()
        return {"started_domains": started_domains}

    def run(self):
        """
        Start all default domains for each configured pool, analyze statistics to evaluate hardware performance and stop them.
        For real and exat evaluate must be run without any other domains running.
        :return:
        """
        data = {}

        data_create = self.create_domains()  # Create domains if necessari
        sleep(data_create.get("total_created_domains"))  # Wait 1 sec more for each created domain.
        data_stop = self.stop_domains()  # Stop domains if necessari
        sleep(data_stop.get("total_stopped_domains"))  # Wait 1 sec more for each stopped domain.
        # Start domains and evaluate
        data_start = self.start_domains()
        data.update(data_start)
        # self.stop_domains()
        return data

    def _create_eval_domain(self, id_t, i):
        d = DICT_CREATE.copy()
        t = get_domain(id_t)
        id_domain = "_eval_{}_{}".format(id_t, i)
        disk_path = "{}/{}/{}/{}.qcow2".format(self.user['category'], self.user['group'], self.user['id'], id_domain)
        d['create_dict']['hardware']['disks'][0]['file'] = disk_path
        d['create_dict']['hardware']['disks'][0]['parent'] = t['disks_info'][0]['filename']
        d['create_dict']['origin'] = t['id']
        d['id'] = id_domain
        d['name'] = id_domain[1:]  # remove first char
        d['icon'] = t['icon']
        d['os'] = t['os']
        insert_domain(d)

    def _evaluate(self):
        """
        Evaluate pool resources.
        If pool arrive to Threshold, return False
        :param id_pool:
        :return:
        """
        for h in self.hyps:
            statistics = h.get_eval_statistics()
            cond_1 = statistics["cpu_percent_free"] < 10
            cond_2 = statistics["ram_percent_free"] < h.percent_ram_template
            eval_log.debug("EVALUATE - Hyp: {}, cpu: {}, "
                           "ram: {}, ram_template: {}".format(h.id,
                                                       statistics["cpu_percent_free"],
                                                       statistics["ram_percent_free"],
                                                       h.percent_ram_template))
            condition_list = [cond_1, cond_2]
            if any(condition_list):  # Enter if there is any True value on condition_list
                eval_log.debug("EVALUATE - Return False")
                return False
        return True

    def _get_domains_id_randomized(self):
        dd = self.defined_domains
        domains_id_list = []
        for t in self.templates:
            n_dd = dd[t['id']]  # defined domains number
            ids = get_domains_id(self.user["id"], self.id_pool, origin=t['id'])
            shuffle(ids)
            if len(ids) < n_dd:
                error_msg = "Error starting domains for eval template {}," \
                            " needs {} domains and have {}".format(t['id'], n_dd, len(ids))
                eval_log.error(error_msg)
                return {"error": error_msg}
            [domains_id_list.append(ids.pop()) for i in range(n_dd)]
        return domains_id_list
