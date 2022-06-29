import requests as r
from bs4 import BeautifulSoup
import re
import argparse
import sys
from queue import Queue
from ratelimiter import RateLimiter
import time

exclude = r'.*?((category|special|help)?:|(main_page|terms_of_use|wikipedia|privacy_policy).?)'
base_url = 'https://en.wikipedia.org'


def parse_cla():
    parser = argparse.ArgumentParser(
        description='Find link trail between two wiki articles. Example usage: ./wiki_url_searcher.py -r 10 -s https://en.wikipedia.org/wiki/Six_degrees_of_separation -t https://en.wikipedia.org/wiki/Paramount_Pictures')

    parser.add_argument('-s', '--start_url', type=str,
                              help='Start URL', default='https://en.wikipedia.org/wiki/Six_degrees_of_separation')
    parser.add_argument('-t', '--target_url', type=str,
                              help='Target URL', default='https://en.wikipedia.org/wiki/Paramount_Pictures')
    parser.add_argument('-d', '--depth', type=int,
                              help='Maximum link depth', default=5)
    parser.add_argument('-r', '--rate_limit', type=int,
                              help='RPS', default=10)

    return parser.parse_args()


def limited(until):
    duration = int(round(until - time.time()))
    print(f'Rate limited, sleeping for {duration} seconds')


def BFS(start_url, target_url, rate_limiter, depth=5, ):
    level = {}
    level[start_url] = -1
    visited = set()
    queue = Queue()
    queue.put(start_url)
    visited.add(start_url)
    parent = dict()
    parent[start_url] = None
    path_found = False
    while not queue.empty() and not path_found:
        current_url = queue.get()
        if level[current_url] > depth:
            print("Depth overflow")
            return

        with rate_limiter:
            page = r.get(base_url + current_url).text

        edges = [l['href'].lower() for l in BeautifulSoup(page, 'lxml').find_all("a", attrs={
            "class": None, "id": None, "accesskey": None, "href": re.compile(r"^(/wiki/[^:]+)$")})]
        edges = list(set(edges).difference(visited))
        for next_url in edges:
            queue.put(next_url)
            parent[next_url] = current_url
            level[next_url] = level[current_url]+1
            visited.add(next_url)
            if next_url == target_url:
                path_found = True
                print("Found at depth:", level[next_url])
                break
    path = []
    if path_found:
        path.append(target_url)
        while parent[target_url] is not None:
            path.append(parent[target_url])
            target_url = parent[target_url]
        path.reverse()
    return ' -> '.join(path)


if __name__ == "__main__":
    args = parse_cla()
    base_url = args.start_url.split('.org')[0] + '.org'
    args.start_url = args.start_url.split('.org')[1].lower()
    args.target_url = args.target_url.split('.org')[1].lower()
    rate_limiter = RateLimiter(
        max_calls=args.rate_limit, period=1, callback=limited)
    try:
        print(BFS(args.start_url, args.target_url, rate_limiter, args.depth))
    except KeyboardInterrupt:
        if input('Interrupt task? (Y/n): ') != 'n':
            sys.exit()
