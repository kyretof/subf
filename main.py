from pathlib import Path
from curl_cffi import requests
import argparse
import re
from time import sleep

# Optional for pretty CLI output
try:
    from rich import print
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    def print(*args, **kwargs):
        __builtins__.print(*args, **kwargs)
    Progress = None

def is_valid_domain(domain: str) -> bool:
    """
    Validates if the given string is a proper domain name using regex.

    Args:
        domain (str): Domain name to validate (e.g., "example.com")

    Returns:
        bool: True if domain is valid, else False.
    """
    return re.match(r'^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$', domain) is not None


def get_crt(subdomain: str):
    """
    Fetches certificate data for a domain from crt.sh.

    Args:
        subdomain (str): The domain to search for (e.g., "example.com")

    Returns:
        list | None: Parsed JSON data if found, else None.
    """
    url = f'https://crt.sh/?q={subdomain}&output=json'
    s = requests.Session()
    try:
        req = s.get(url, impersonate='chrome', timeout=60)
        if req.status_code == 200:
            datas = req.json()
            if datas:
                return datas
    except requests.Timeout:
        print('[red]Request timed out[/red]')
    except Exception as e:
        print(f'[red]Error: {e}[/red]')

    return None


def clean_subd(subdomain: str):
    """
    Cleans up a subdomain string by removing unwanted prefixes like "*." and "www."

    Args:
        subdomain (str): Raw subdomain string

    Returns:
        str: Cleaned subdomain
    """
    if not subdomain:
        return ''
    subdomain = subdomain.strip()
    if subdomain.startswith('*'):
        subdomain = subdomain[2:]
    if subdomain.startswith('www.'):
        subdomain = subdomain[4:]
    return subdomain


def process_data(datas: list):
    """
    Processes the JSON data from crt.sh into a clean set of unique subdomains.

    Args:
        datas (list): JSON list of certificate records

    Returns:
        set: Unique subdomains
    """
    subdomains = set()
    for data in datas:
        common_name = clean_subd(data.get('common_name', ''))
        if common_name:
            subdomains.add(common_name)

        name_value = data.get('name_value', '')
        if '\n' in name_value:
            names = name_value.split('\n')
            for name in names:
                cleaned = clean_subd(name)
                if cleaned:
                    subdomains.add(cleaned)
        else:
            cleaned = clean_subd(name_value)
            if cleaned:
                subdomains.add(cleaned)
    return subdomains


def write_subs_file(file_to_save: str, subdomains: list):
    """
    Writes subdomains to a text file, one per line.

    Args:
        file_to_save (str): Full path to save the file
        subdomains (list): List of cleaned subdomains
    """
    with open(file_to_save, 'w', encoding='utf-8') as f:
        for subdomain in sorted(subdomains):
            f.write(subdomain + '\n')


def main():
    """
    Main entry point for the CLI tool.
    Parses arguments, validates the domain, fetches and processes data,
    and writes results to a file.
    """
    parser = argparse.ArgumentParser(
        description='Fetch subdomains from crt.sh using Certificate Transparency logs.'
    )
    parser.add_argument('domain', help='The domain to search for subdomains (e.g., example.com)')
    parser.add_argument('-o', '--output', help='Output file name', default=None)
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()
    domain = args.domain

    # Validate domain format
    if not is_valid_domain(domain):
        print(f"[red]❌ '{domain}' is not a valid domain name.[/red]")
        return

    # Determine output file name
    output_file = args.output or f'{domain.replace(".com", "")}-subdomains.txt'
    save_path = Path.cwd() / output_file

    # Use fancy progress bar if available
    if Progress:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Fetching subdomains...", total=None)
            data = get_crt(domain)
            progress.update(task, description="Processing data...")
            sleep(0.5)
            if data:
                subdomains = process_data(data)
                write_subs_file(save_path, subdomains)
                progress.update(task, description="Done!")
                print(f"[green]✔ Found {len(subdomains)} subdomains. Saved to [bold]{save_path}[/bold][/green]")
            else:
                print("[yellow]⚠ No results found[/yellow]")
    else:
        # Fallback plain output
        print(f"Fetching subdomains for {domain}...")
        data = get_crt(domain)
        if data:
            subdomains = process_data(data)
            write_subs_file(save_path, subdomains)
            print(f"Found {len(subdomains)} subdomains. Saved to {save_path}")
        else:
            print("No results found.")


if __name__ == '__main__':
    main()
