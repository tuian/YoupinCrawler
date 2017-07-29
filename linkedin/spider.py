from linkedin import login, contact, model
import yplog
import requests
import time

log = yplog.YPLogger('spider', 'linkedin')


def check_account(status=1):
    # 批量检测所有账户是否正常
    log.info('开始账户检测！')
    if status is None:
        accounts = model.SjUser.select()
    elif type(status) == dict:
        accounts = model.SjUser.select().where(
            model.SjUser.status << status)
    else:
        accounts = model.SjUser.select().where(
            model.SjUser.status == status)
    for account in accounts:
        login.s = requests.session()
        login.check_login(account)
        time.sleep(4)
    log.info('账户检测完毕！')


def crawl_contact(n=1):
    log.info('开始爬取联系人！')
    max_count = model.SjUser.select(model.fn.Max(model.SjUser.resume_count)).scalar()
    count = 200
    for start in range((n-1)*count, max_count, count):
        accounts = model.SjUser.select().where(
            model.SjUser.status == 1)
        for account in accounts:
            if account.resume_count < start:
                continue
            login.s = requests.session()
            me = login.login(account)
            # 如果返回值不是字典类型，说明登录失败，修改账号状态
            if type(me) is not dict:
                account.status = me
                account.save()
                continue
            contact.client_page_id = me['clientPageId']
            contact.csrf_token = me['csrfToken']
            contact.s = login.s
            connection_list = contact.crawl_connections(start, count)
            for connection in connection_list:
                pub_id = connection['pub']
                linkedin_id = connection['linkedin']
                if not model.is_exist(model.SjBasic, linkedin_id):
                    data = contact.crawl_detail(pub_id)
                    if not data:
                        continue
                    model.init_basic(data['basic'])
                    for job in data['career']:
                        model.insert_work(job, linkedin_id)
                    for edu in data['education']:
                        model.insert_edu(edu, linkedin_id)
                    for project in data['projects']:
                        model.insert_project(project, linkedin_id)
                    time.sleep(1)
        log.info('第{0}次循环爬取完成'.format(int(start/count) + 1))
        time.sleep(60)
    log.info('所有账户的联系人爬取完毕！')


def crawl_detail(pub_id):
    login.s = requests.session()
    me = login.login()
    contact.client_page_id = me['clientPageId']
    contact.csrf_token = me['csrfToken']
    contact.s = login.s
    data = contact.crawl_detail(pub_id)
    return data

if __name__ == '__main__':
    import sys
    if 'check' in sys.argv:
        check_account(2)

    if 'contact' in sys.argv:
        crawl_contact()
    crawl_detail('宇泽-徐-3510b8b7')
