# -*- coding: utf-8 -*-

import parameters
import feedparser

LEGITIMATE_FEEDS = {
    #BBC RSS List: http://www.bbc.com/news/10628494
    'BBC Top Stories': 'http://feeds.bbci.co.uk/news/rss.xml',
    'BBC Technology': 'http://feeds.bbci.co.uk/news/technology/rss.xml',
    'Yahoo': 'http://news.yahoo.com/rss/',
    'Sky News': 'http://news.sky.com/info/rss',
    #Reuter RSS list: http://www.reuters.com/tools/rss
    'Reuter Top News': 'http://feeds.reuters.com/reuters/topNews',
    #'Reuter Entertainment': 'http://feeds.reuters.com/reuters/entertainment',
    #'Engadget': 'https://www.engadget.com/rss.xml',
    'New Scientist': 'http://feeds.newscientist.com'
}

ILLEGITIMATE_FEEDS = {
    #https://en.wikipedia.org/wiki/List_of_fake_news_websites
    'Natural News': 'http://www.naturalnews.com/rss.xml',
    #'Snopes': 'http://www.snopes.com/info/whatsnew.xml',
    'The Spoof Front Page': 'http://www.thespoof.com/rss/feeds/frontpage/rss.xml',
    #'The Spoof US': 'http://www.thespoof.com/rss/feeds/us/rss.xml',
    #'The Spoof UK': 'http://www.thespoof.com/rss/feeds/uk/rss.xml',
    'The Spoof World News': 'http://www.thespoof.com/rss/feeds/world/rss.xml',
    #'The Spoof Entertainment & Gossip': 'http://www.thespoof.com/rss/feeds/entertainment/rss.xml',
    'The Spoof Science & Technology': 'http://www.thespoof.com/rss/feeds/science/rss.xml',
    #'The Spoof Sport Headlines': 'http://www.thespoof.com/rss/feeds/sport/rss.xml',
    #'The Spoof Business Brief': 'http://www.thespoof.com/rss/feeds/business/rss.xml',
    #'Blacklisted News': 'http://feeds.feedburner.com/blacklistednews/hKxa?format=xml'
    #http://www.insanejournal.com/syn/raw.bml
    #http://www.fakenewschecker.com/
    #http://21stcenturywire.com/feed/
    #http://100percentfedup.com/feed/
}

#d['entries'][0].keys()
#['summary_detail', 'published_parsed', 'links', 'title', 'tags', 'summary', 'title_detail', 'link', 'published']

#d.feed.published_parsed
#title, link, description, publication date, and entry ID

def validHeadline(h):
    return len(h.split())>=5 and not h.endswith('?')

def getTitles(url_list):
    result = []
    for url in url_list:
        d = feedparser.parse(url)
        titles = [x['title'].encode('utf-8').strip() for x in d['entries']]
        titles = [x for x in titles if validHeadline(x)]
        result.extend(titles)
    return list(set(result))

def getLegitimateHeadlines():
    return getTitles(LEGITIMATE_FEEDS.values())

def getIllegitimateHeadlines():
    return getTitles(ILLEGITIMATE_FEEDS.values())
