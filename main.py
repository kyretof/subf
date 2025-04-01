from pathlib import Path
from curl_cffi import requests


def get_crt(subdomain: str):
    '''
    Fetches subdomains from crt.sh (a public Certificate Transparency log)
    It scrapes the subdomains by querying the domain and processing the response.

    Args:
    subdomain (str): The domain to query against crt.sh to find associated subdomains.

    Returns:
    data: JSON format of the subdomains || None if there are no result
    '''
    url = f'https://crt.sh/?q={subdomain}&output=json'
    s = requests.Session()

    try:
        req = s.get(url, impersonate='chrome', timeout=60)

        if req.status_code == 200:
            datas = req.json()
            if datas:
                return datas
    except requests.Timeout:
        print('Request timedout')
        return None

    return None


def clean_subd(subdomain: str):
    '''
    Cleans the subdomain and removes *. , www, and \n or \r

    Args:
    subdomain (str): common_name

    Returns:
    subdomain: Cleaned subdomain
    '''

    subdomain = subdomain.strip()

    if subdomain.startswith('*'):
        subdomain = subdomain[2:]

    if subdomain.startswith('www.'):
        subdomain = subdomain[4:]

    return subdomain


def process_data(datas: list):
    '''
    Processes the data:
        - clean data using clean_subd(name: str) function
        - fix trailing spaces \n, will process it one by one in a loop
        - saves it to a set

    Args:
    datas: list (JSON)

    Returns:
    subdomains: set, unique
    '''

    subdomains = set()
    for data in datas:
        common_name = data.get('common_name')
        common_name = clean_subd(common_name)
        subdomains.add(common_name)

        name_value = data.get('name_value')
        # Contains multiple value e.g domain.com\nsub.domain.com\ntest.domain.com
        if '\n' in name_value:
            names = name_value.split('\n')
            for name in names:
                name_value = clean_subd(name)
                subdomains.add(name_value)
        else:
            name_value = clean_subd(name_value)
            subdomains.add(name_value)

    return subdomains


def write_subs_file(file_to_save: str, subdomains: list):
    '''
    Write subdomains (list) to a file (txt)

    Args:
    file_name: str
    subdomains: list
    '''
    with open(file_to_save, 'w', encoding='utf-8') as f:
        for subdomain in subdomains:
            f.write(subdomain + '\n')


def main():
    '''
    Main file
    '''
    domain = input('Enter subdomain: ')
    data = get_crt(domain)

    # There is JSON data
    if data:
        subdomains = process_data(data)
        subdomains = list(subdomains)
        file_name = f'{domain.replace(".com", "")}-subdomains.txt'
        save_path = Path.cwd() / file_name
        write_subs_file(save_path, subdomains)
    else:
        print('No result found')


if __name__ == '__main__':
    main()
