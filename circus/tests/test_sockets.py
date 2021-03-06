import os
import socket
import tempfile
try:
    import IN
except ImportError:
    pass
import mock

from circus.tests.support import TestCase, skipIf, EasyTestSuite
from circus.sockets import CircusSocket, CircusSockets


def so_bindtodevice_supported():
    try:
        if hasattr(IN, 'SO_BINDTODEVICE'):
            return True
    except NameError:
        pass
    return False


class TestSockets(TestCase):

    def test_socket(self):
        sock = CircusSocket('somename', 'localhost', 0)
        try:
            sock.bind_and_listen()
        finally:
            sock.close()

    def test_manager(self):
        mgr = CircusSockets()

        for i in range(5):
            mgr.add(str(i), 'localhost', 0)

        port = mgr['1'].port
        try:
            mgr.bind_and_listen_all()
            # we should have a port now
            self.assertNotEqual(port, mgr['1'].port)
        finally:
            mgr.close_all()

    def test_load_from_config_no_proto(self):
        """When no proto in the config, the default (0) is used."""
        config = {'name': ''}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.proto, 0)
        sock.close()

    def test_load_from_config_unknown_proto(self):
        """Unknown proto in the config raises an error."""
        config = {'name': '', 'proto': 'foo'}
        self.assertRaises(socket.error, CircusSocket.load_from_config, config)

    def test_load_from_config_umask(self):
        fd, sockfile = tempfile.mkstemp()
        os.close(fd)
        os.remove(sockfile)

        config = {'name': 'somename', 'path': sockfile, 'umask': 0}
        sock = CircusSocket.load_from_config(config)
        try:
            self.assertEqual(sock.umask, 0)
        finally:
            sock.close()

    def test_unix_socket(self):
        fd, sockfile = tempfile.mkstemp()
        os.close(fd)
        os.remove(sockfile)

        sock = CircusSocket('somename', path=sockfile, umask=0)
        try:
            sock.bind_and_listen()
            self.assertTrue(os.path.exists(sockfile))
            permissions = oct(os.stat(sockfile).st_mode)[-3:]
            self.assertEqual(permissions, '777')
        finally:
            sock.close()

    def test_unix_cleanup(self):
        sockets = CircusSockets()
        fd, sockfile = tempfile.mkstemp()
        os.close(fd)
        os.remove(sockfile)

        try:
            sockets.add('unix', path=sockfile)
            sockets.bind_and_listen_all()
            self.assertTrue(os.path.exists(sockfile))
        finally:
            sockets.close_all()
            self.assertTrue(not os.path.exists(sockfile))

    @skipIf(not so_bindtodevice_supported(),
            'SO_BINDTODEVICE unsupported')
    def test_bind_to_interface(self):
        config = {'name': '', 'host': 'localhost', 'port': 0,
                  'interface': 'lo'}

        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.interface, config['interface'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            sock.setsockopt.assert_any_call(socket.SOL_SOCKET,
                                            IN.SO_BINDTODEVICE,
                                            config['interface'] + '\0')
        finally:
            sock.close()

    def test_inet6(self):
        config = {'name': '', 'host': '::1', 'port': 0,
                  'family': 'AF_INET6'}
        sock = CircusSocket.load_from_config(config)
        self.assertEqual(sock.host, config['host'])
        self.assertEqual(sock.port, config['port'])
        sock.setsockopt = mock.Mock()
        try:
            sock.bind_and_listen()
            # we should have got a port set
            self.assertNotEqual(sock.port, 0)
        finally:
            sock.close()

test_suite = EasyTestSuite(__name__)
