from datetime import datetime
from time import sleep

import pymongo
import requests


def send_query(p, is_arxiv):
    p_id = p['_id']
    prefix = "arXiv:" if is_arxiv else ""
    response = requests.get(f'https://api.semanticscholar.org/v1/paper/{prefix}{p_id}').json()
    if 'error' in response:
        print(f'Error - {p_id} - {response}')
        return None

    authors = [{'id': a['authorId'], 'name': a['name']} for a in response['authors']]
    citations = [{'arxivId': c['arxivId'], 'paperId': c['paperId'], 'title': c['title']} for c in response['citations']]
    references = [{'arxivId': r['arxivId'], 'paperId': r['paperId'], 'title': r['title']} for r in
                  response['references']]
    print(p_id)
    return {
        '_id': response['arxivId'], 'paperId': response['paperId'], 'year': response['year'],
        'time_updated': p.get('time_updated', None), 'time_published': p.get('time_published', None),
        'title': response['title'], 'authors': authors, 'citations': citations, 'references': references,
        'last_rec_update': datetime.utcnow(), 'found': 1
    }


def fetch_paper_data(p, is_arxiv=True):
    p_id = p['_id']
    res = send_query(p, is_arxiv)
    if not res:
        return {'_id': p_id, 'title': p['title'], 'authors': p['authors'],
                'last_rec_update': datetime.utcnow(), 'time_updated': p['time_updated'],
                'time_published': p['time_published'],
                'found': 0}
    return res


if __name__ == '__main__':
    SEM_FIELD = 'semanticscholar'
    min_days_to_update = 7 * 86400  # 7 days

    client = pymongo.MongoClient()
    mdb = client.arxiv
    db_papers = mdb.papers
    sem_sch_papers = mdb.sem_sch_papers # semantic scholar data
    sem_sch_authors = mdb.sem_sch_authors # semantic scholar data

    papers = list(db_papers.find())
    for p in papers:
        cur_sem_sch = sem_sch_papers.find_one({'_id': p['_id']})
        if not cur_sem_sch or (datetime.utcnow() - cur_sem_sch['last_rec_update']).total_seconds() > min_days_to_update:
            res = fetch_paper_data(p)
            sem_sch_papers.update({'_id': res['_id']}, {'$set': res}, True)
            for a in res['authors']:
                sem_sch_authors.update({'_id': a['name']}, {}, True)
            sleep(0.2)
        else:
            print('Paper is already in DB')




