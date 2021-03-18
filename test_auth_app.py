import os
import sys
import argparse

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from test_auth_app.backend import test_auth_app_flask

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=7767, required=False, help='service port')
    parser.add_argument('--host', type=str, default='0.0.0.0', required=False, help='server host')
    parser.add_argument('--data', type=str, default='./data/', required=False, help='path to data-directory')
    args = parser.parse_args()
    #
    print('params: [{}]'.format(parser))
    if (args.port is None) or (args.host is None):
        p_port = 7767
        p_host = '0.0.0.0'
    else:
        p_port = args.port
        p_host = args.host
    print('Go to URL: https://{}:{}'.format(p_host, p_port))
    test_auth_app_flask.run(host=p_host, port=p_port, debug=True, use_reloader=True, ssl_context='adhoc')
