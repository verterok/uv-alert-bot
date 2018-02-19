# blocking ftp server 
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed
import os
pyftpdlib_logger = logging.getLogger('pyftpdlib')
pyftpdlib_logger.propagate = False


class FTPAuthorizer(DummyAuthorizer):

    user_table = {}

    def set_credentials(self, username, password, homedir):
        self.username = username
        self.password = password 
        self.homedir = homedir

    def validate_authentication(self, username, password, handler):
        if not (username == self.username and password == self.password):
            raise AuthenticationFailed
        perm = 'elradfmwM'  # CWD, LIST and STOR
        homedir = self.homedir
        if not os.path.exists(homedir):
            os.makedirs(homedir)
        msg_login = 'Welcome aboard user!'
        msg_quit = 'See you soon!'
        dic = {'home': homedir,
               'perm': perm,
               'operms': {},
               'msg_login': str(msg_login),
               'msg_quit': str(msg_quit)
               }
        self.user_table[username] = dic


class MyFTPHandler(FTPHandler):

    def publish_event(self, topic, message):
        self.bot_queue.ftp_event(topic, message)

    def on_file_received(self, filepath):
        topic = 'ftpd_file_received'
        self.publish_event(topic, filepath)

    def on_incomplete_file_received(self, filepath):
        topic = 'ftpd_file_received'
        self.publish_event(topic, filepath)


def run_ftpd(host, port, alert_bot, username, password, homedir):
    authorizer = FTPAuthorizer()
    authorizer.set_credentials(username, password, homedir)
    handler = MyFTPHandler
    handler.bot_queue = alert_bot
    handler.authorizer = authorizer
    server = FTPServer((host, port), handler)
    server.serve_forever()

