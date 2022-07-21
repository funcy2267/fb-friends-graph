import argparse
import pickle
import time
import json
import os
from multiprocessing.pool import ThreadPool
from bs4 import BeautifulSoup
from selenium import webdriver

parser = argparse.ArgumentParser(description='Make a connection graph between friends on Facebook.')
parser.add_argument('--user', '-u', default='profile.php', help='username to start scanning (if not specified, scanning will start from your profile)')
parser.add_argument('--depth', '-d', type=int, default=1, help='crawling depth (friends of friends)')
parser.add_argument('--pause', '-p', type=int, default=1, help='seconds to pause before going to next page')
parser.add_argument('--noscroll', action='store_true', help='do not scroll pages')
parser.add_argument('--force', '-f', action='store_true', help='scan already scanned users')
parser.add_argument('--blacklist', '-b', help='blacklist users (usernames separated with spaces)')
parser.add_argument('--output', '-o', default='Friends/', help='output folder (followed by slash)')
parser.add_argument('--limit', '-l', type=int, help='limit users in queue to scan')
parser.add_argument('--cookies', '-c', default='cookies.pkl', help='use custom cookies file')
parser.add_argument('--threads', '-t', type=int, default=1, help='number of threads')
args = parser.parse_args()

FB_BASE_URL = 'https://m.facebook.com/'
users_db_file = args.output+'users_db.json'

# open url
def open_url(url, tab, scroll_down=False):
    driver = drivers[tab]
    driver.get(url)

    if scroll_down == True:
        while True:
            src1 = driver.page_source
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            src2 = driver.page_source
            if src1 == src2:
                break

    time.sleep(args.pause)
    return(driver.page_source)

# get full name of user
def get_full_name(username, tab):
    raw_html = open_url(FB_BASE_URL+username, tab)
    content = BeautifulSoup(raw_html, "html.parser").find('h3', {"class": "_6x2x"})
    return(content.prettify().split('\n')[1].strip())

def get_link_joiner(username):
    link_joiners = ['?', '&']
    if 'profile.php?id=' in username:
        link_joiner = link_joiners[1]
    else:
        link_joiner = link_joiners[0]
    return(link_joiner)

# get list of friends from user
def get_friends(username, tab):
    link_joiner = get_link_joiner(username)
    raw_html = open_url(FB_BASE_URL+username+link_joiner+'v=friends', tab, scroll_down=not args.noscroll)
    content = BeautifulSoup(raw_html, "html.parser").find('div', {"id": "root"})
    page_a = content.find_all('a', href=True)

    banned_usernames = ['home.php', 'buddylist.php', '']
    banned_in_usernames = ['/']
    friends = {}
    i=0
    for a in page_a:
        href = a['href']
        href_username = href[1:]
        username = href_username.split(get_link_joiner(href_username))[0]
        try:
            full_name = page_a[i+1].getText()
        except IndexError:
            pass
        if not any(x for x in [any(x in username for x in banned_in_usernames), any(username == x for x in banned_usernames), username in friends]):
            friends[username] = full_name
        i+=1
    return(friends)

# save friends data in proper format
def save_to_graph(full_name, friends):
    f = open(args.output+full_name+".md", "a", encoding="utf-8")
    for friend in friends:
        try:
            f.write('[['+friends[friend]+']]'+'\n')
        except UnicodeEncodeError:
            pass
    f.close()

def exec_queue(queue, tab):
    display_thread = str(tab+1)
    print("In queue (thread "+display_thread+"):", queue, '\n')
    result = {}
    queue_index = 1
    for user in queue:
        if args.limit != None and queue_index > args.limit:
            print("Limit reached.")
            break
        print("Current user:", user, "(thread "+display_thread+", "+str(queue_index)+'/'+str(len(queue))+")")
        result[user] = get_friends(user, tab)
        queue_index += 1
    return(result)

def start_crawling(username, depth):
    if os.path.isfile(users_db_file):
        users_db = json.load(open(users_db_file, "r", encoding="utf-8"))
    else:
        users_db = {"full_names": {}, "friends": {}}

    if username not in users_db["full_names"]:
        users_db["full_names"][username] = get_full_name(username, 0)

    queue = [username]
    next_round = []
    users_scanned = []

    # import blacklist
    blacklist = []
    if args.blacklist != None:
        blacklist += args.blacklist.split(" ")
        print("Blacklisted users:", blacklist)

    # import already scanned users
    already_scanned = []
    if not args.force:
        already_scanned += list(users_db["friends"])
        print("Already scanned users:", already_scanned)

    # scanning system
    next_result = {}
    for depth_index in range(depth):
        display_depth = str(depth_index+1)
        print('\n'+"Current depth:", display_depth)

        queue_divided = {}
        for thread in range(args.threads):
            queue_divided[thread] = []
            for i in range(thread, len(queue), args.threads):
                queue_divided[thread] += [queue[i]]

        thread_pools = {}
        thread_results = {}
        for thread in queue_divided:
            thread_pools[thread] = ThreadPool(processes=1)
            thread_results[thread] = thread_pools[thread].apply_async(exec_queue, (queue_divided[thread], thread))

        queue_result = next_result
        for thread in thread_results:
            queue_result.update(thread_results[thread].get())

        # get existing friends data
        next_result = {}
        for user in queue_result:
            friends_1 = queue_result[user]
            for friend_1 in friends_1:
                if friend_1 in already_scanned:
                    next_result[friend_1] = {}
                    friends_2 = users_db["friends"][friend_1]
                    for friend_2 in friends_2:
                        next_result[friend_1][friend_2] = users_db["full_names"][friend_2]

        for user in queue_result:
            friends = queue_result[user]
            full_name = users_db["full_names"][user]

            users_db["full_names"].update(friends)
            if user not in users_db["friends"]:
                users_db["friends"][user] = list(friends)
            else:
                for friend in friends:
                    if friend not in users_db["friends"][user]:
                        users_db["friends"][user] += [friend]
            if user not in users_scanned:
                users_scanned += [user]

            # save connections between friends
            save_to_graph(full_name, friends)

            for friend in friends:
                if not any(friend in x for x in [queue, users_scanned, next_round, blacklist, already_scanned]):
                    next_round += [friend]

        queue = next_round
        next_round = []

    # dump users database
    json.dump(users_db, open(users_db_file, "w", encoding="utf-8"), indent=2)

    # print summary
    print('\n'+"Users scanned:", ", ".join(users_scanned))
    print("Total users scanned:", len(users_scanned))

# create output folder if not exists
if not os.path.isdir(args.output):
    os.mkdir(args.output)

# prepare browser threads
print("Launching Firefox...")
drivers = []
for thread in range(args.threads):
    print("Opening tab", str(thread+1)+'/'+str(args.threads)+"...")
    drivers += [webdriver.Firefox()]
    open_url('https://www.facebook.com', thread)
    cookies = pickle.load(open(args.cookies, "rb"))
    for cookie in cookies:
        drivers[thread].add_cookie(cookie)
print("All tabs have been opened.")

# start crawling
start_crawling(args.user, args.depth)

# close browser threads
for driver in drivers:
    driver.close()
print("Finished.")
