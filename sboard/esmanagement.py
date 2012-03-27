import json
import os
import subprocess
import time
import urllib2
import urlparse

import psutil

from pyes.rivers import CouchDBRiver

from . import es
from .models import Node


class ESManagementException(Exception):
    pass


class ESManagement(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.pid_file = os.path.join(self.path, 'PID')
        self.elasticsearch = os.path.join(self.path, 'bin', 'elasticsearch')

        if not os.path.exists(self.elasticsearch):
            raise ESManagementException(
                    "'bin/elasticsearch' does not exist in path: "
                    "%s" % path)

    def check(self, timeout=1):
        try:
            f = urllib2.urlopen("http://localhost:9200/", timeout=timeout)
        except urllib2.URLError:
            return False

        data = f.read()
        data = json.loads(data)
        f.close()

        return data['status'] == 200 and data['ok']

    def get_pid(self):
        if os.path.exists(self.pid_file):
            with open(self.pid_file) as f:
                return int(f.read())

    def get_process(self, pid):
        try:
            return psutil.Process(pid)
        except psutil.NoSuchProcess:
            return None

    def terminate(self, pid):
        process = self.get_process(pid)
        if process:
            process.terminate()
            try:
                process.wait(10)
            except psutil.TimeoutExpired:
                process.kill()

    def find_all_demons(self):
        arg = "-Des.path.home=%s" % self.path
        for p in psutil.process_iter():
            if p.name == 'java' and arg in p.cmdline:
                yield p.pid

    def install(self):
        uri = Node.get_db().uri
        uri = urlparse.urlparse(uri)
        params = {
            'index_name': 'sboard',
            'index_type': 'allnodes',
            'host': uri.hostname,
            'port': uri.port,
            'db': uri.path.split('/')[1],
        }

        if uri.username:
            params['user'] = uri.username
        if uri.password:
            params['password'] = uri.password

        river = CouchDBRiver(**params)
        es.conn.create_river(river, river_name='sboard')

    def is_installed(self):
        try:
            f = urllib2.urlopen("http://localhost:9200/_river/sboard/_status")
        except urllib2.HTTPError:
            return False
        data = f.read()
        f.close()
        data = json.loads(data)
        return data['exists']


    def get_running_time(self):
        if os.path.exists(self.pid_file):
            return time.time() - os.path.getmtime(self.pid_file)
        else:
            return None

    def is_just_started(self):
        """Returns True if ElasticSearch is started less that 30 minutes ago.
        """
        running = self.get_running_time()
        return running is not None and running <= 30

    def wait(self, timeout=60):
        seconds = 0
        while True:
            if self.check():
                return True
            elif seconds > timeout:
                return False
            else:
                time.sleep(1)

    def start(self):
        return subprocess.Popen([self.elasticsearch, '-p', self.pid_file],
                                env={"ES_MIN_MEM": "128m",
                                     "ES_MAX_MEM": "256m"})

    def stop(self):
        pid = self.get_pid()
        if pid:
            self.terminate(pid)

        for pid in self.find_all_demons():
            self.terminate(pid)
