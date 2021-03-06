import requests
from bs4 import BeautifulSoup
import re
import html
from urllib.parse import unquote
import json
import ypconfig
import yplog
import decrypt
from linkedin import contact
import pickle
import os
import base64
import time

config = ypconfig.config
# print(config)

log = yplog.YPLogger('login', 'linkedin')
s = requests.Session()
root_path = os.path.dirname(__file__)
cache_dir = os.path.join(root_path, 'sessions')


def login(account=None, username='', password=''):
    """
    模拟登录
    :param account: 账号对象
    :param username: 用户名
    :param password: 用户密码
    :return:
    """
    login_url = 'https://www.linkedin.com/uas/login'
    login_submit_url = 'https://www.linkedin.com/uas/login-submit'
    lr = s.get(login_url)
    if lr.status_code == 200:
        soup = BeautifulSoup(lr.text, "lxml")
        soup = soup.find(id="login")
        # 提取loginCsrfParam 和 csrfToken
        loginCsrfParam = soup.find('input', id='loginCsrfParam-login')['value']
        csrfToken = soup.find('input', id='csrfToken-login')['value']
    else:
        log.warn("""访问登录页面被拒绝:{0}
        {1}""".format(lr.status_code, lr.text))
        log.warn(lr.url + '\n' + lr.text)
        return -3
    # 模拟登录
    try:
        if username == '':
            username = account.username
            password = decrypt.think_decrypt(account.password,
                                             config['linkedin']['key'])
    except AttributeError:
        username = config['linkedin']['username']
        password = config['linkedin']['password']
    log.info('{0}准备登录'.format(username))
    login_data = dict(session_key=username, session_password=password,
                      isJsEnabled='false', loginCsrfParam=loginCsrfParam)
    lsr = s.post(login_submit_url, data=login_data)
    if lsr.status_code == 200:
        if re.search('There were one or more errors in your submission', lsr.text):
            log.warn('{0}账户或密码错误！'.format(username))
            return -1
        if re.search('Sign-In Verification|Verify your identity', lsr.text):
            if re.search('Sorry, we need you to reset your password', lsr.text):
                log.warn('{0}需要重置密码！'.format(username))
                return -2
            log.warn('{0}需要验证！'.format(username))
            params = get_verify_params(lsr.text)
            cache_session(username, params)
            return 2
        if re.search('You are signing in from an unrecognized device', lsr.text):
            log.warn('{0}需要授权！'.format(username))
            params = get_verify_params(lsr.text)
            cache_session(username, params)
            return 3

        return parse_login_success(lsr, username, csrfToken)
    else:
        log.warn("""登录请求被拒绝:{0}
                {1}""".format(lr.status_code, lr.text))
        log.warn(lsr.url + '\n' + lsr.text)
        return -3


def parse_login_success(response, username, csrfToken):
    """
    解析登录成功的响应
    :param response: 登录成功后的响应
    :param username: 用户名
    :param csrfToken: 跨域Token
    :return:
    """
    soup = BeautifulSoup(response.text, 'lxml'). \
        find('meta', attrs={'name': 'clientPageInstanceId'})
    if soup is None:
        log.warn('其他未知错误：{0}'.format(response.text))
        return -3
    client_page_id = soup['content']
    text = unquote(html.unescape(response.text).encode(response.encoding).decode())
    soup = BeautifulSoup(text, "lxml")
    soup = soup.find('code', text=re.compile(r'"com.linkedin.voyager.common.Me"'))
    me = json.loads(soup.get_text())
    linkedin_id = pub_id = 0
    for item in me['included']:
        if item['$type'] == 'com.linkedin.voyager.identity.shared.MiniProfile':
            linkedin_id = item.get('objectUrn', '').split(':')[-1]
            pub_id = item['publicIdentifier']
            break
    log.info('{0}登录成功'.format(username))
    params = {'clientPageId': client_page_id,
              'csrfToken': csrfToken,
              'linkedin': linkedin_id,
              'pub_id': pub_id}
    cache_session(username, params, action="login")
    return params


def check_login(account):
    """
    检测当前账号
    :param account:
    :return:
    """
    log.info(account.username + '账户检测')
    me = login(account)
    if type(me) == dict:
        account.lk = me['linkedin']
        contact.s = s
        contact.client_page_id = me['clientPageId']
        contact.csrf_token = me['csrfToken']
        # account.now_count = account.resume_count
        account.resume_count = contact.crawl_cnum()
        account.status = 1
        account.update_time = int(time.time())
        log.info(account.username + '账户可用')
    else:
        account.status = me
    account.save()


def get_verify_params(response):
    """
    获取验证账号
    :param response:
    :return:
    """
    soup = BeautifulSoup(response, "lxml")
    dts = soup.find('input', attrs={'name': 'dts'})['value']
    security_challenge_id = soup.find(
        'input', attrs={'name': 'security-challenge-id'})['value']
    origSourceAlias = soup.find(
        'input', attrs={'name': 'origSourceAlias'})['value']
    csrfToken = soup.find(
        'input', attrs={'name': 'csrfToken'})['value']
    sourceAlias = soup.find(
        'input', attrs={'name': 'sourceAlias'})['value']
    form_data = {'signin': '提交',
                 'security-challenge-id': security_challenge_id,
                 'dts': dts,
                 'origSourceAlias': origSourceAlias,
                 'csrfToken': csrfToken,
                 'sourceAlias': sourceAlias}
    if re.search('You are signing in from an unrecognized device', response):
        form_data['signin'] = '验证'
        form_data['TwoStepVerificationForm_recognizeDevice'] = 'recognize'
    return form_data


def verify(username, v_code, params):
    """
    验证验证码
    :param username:
    :param v_code:
    :param params:
    :return:
    """
    if params['signin'] == '验证':
        verify_url = 'https://www.linkedin.com/uas/two-step-verification-submit'
    else:
        verify_url = 'https://www.linkedin.com/uas/ato-pin-challenge-submit'
    params['PinVerificationForm_pinParam'] = v_code
    vr = s.post(verify_url, data=params)
    if vr.status_code == 200:
        if re.search('The verification code you entered isn\'t valid', vr.text):
            log.warn(username + '验证码无效')
            params = get_verify_params(vr.text)
            cache_session(username, params)
            return -1
        elif re.search('too much time went by', vr.text):
            log.warn(username + '登录超时')
            return -2
        log.info(username + '验证通过')
        log.debug(vr.text)
        params = parse_login_success(vr, username, params['csrfToken'])
        cache_session(username, params, 'login')
        return params
    else:
        log.warn("""登录请求被拒绝:{0}
                        {1}""".format(vr.status_code, vr.text))
        return False


def get_session(username, action='verify'):
    """
    获取会话缓存
    :param username:
    :param action:
    :return:
    """
    session_path = os.path.join(
        cache_dir, action, base64.urlsafe_b64encode(username.encode()).decode())
    if os.path.isfile(session_path):
        log.info(username + "已登录!")
        with open(session_path, 'rb') as f:
            return pickle.load(f)
    else:
        log.warn(username + '会话缓存不存在！')
        return False


def cache_session(username, params, action='verify'):
    """
    缓存会话和必要的参数
    :param username:
    :param params:
    :return:
    """
    session_dir = os.path.join(cache_dir, action)
    if not os.path.isdir(session_dir):
        os.makedirs(session_dir)
    cache_path = os.path.join(
        session_dir, base64.urlsafe_b64encode(username.encode()).decode())
    with open(cache_path, 'wb') as f:
        pickle.dump(dict(session=s, params=params), f)


def exist_session(username, action='login'):
    session_path = os.path.join(
        cache_dir, action, base64.urlsafe_b64encode(username.encode()).decode())
    return os.path.isfile(session_path)

if __name__ == "__main__":
    # s = requests.Session()
    # login()
    # sessionInfo = get_session(config['linkedin']['username'])
    # s = sessionInfo['session']
    # verify_params = sessionInfo['params']
    # verify(config['linkedin']['username'], 853986, verify_params)
    sessionInfo = get_session(config['linkedin']['username'], 'login')
