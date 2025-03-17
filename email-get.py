import socket
import requests
import re
import time
from googlesearch import search
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Function to check open SMTP ports
def check_smtp_port(domain, ports=[25, 465, 587]):
    open_ports = []
    for port in ports:
        try:
            sock = socket.create_connection((domain, port), timeout=5)
            sock.close()
            open_ports.append(port)
        except (socket.timeout, socket.error):
            continue
    return open_ports

# Function to extract emails from a webpage with improved crawling
def extract_emails(url, max_depth=2, visited=None):
    if visited is None:
        visited = set()
    emails = set()
    
    if url in visited or max_depth == 0:
        return emails
    visited.add(url)

    try:
        response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all links for deeper crawling
        links = [a['href'] for a in soup.find_all('a', href=True)]
        links = [link for link in links if link.startswith('http')]

        # Extract emails from text
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails.update(re.findall(email_pattern, soup.get_text()))

        # Crawl deeper
        for link in links[:5]:  # Limit to 5 links per page to avoid excessive requests
            emails.update(extract_emails(link, max_depth - 1, visited))

    except requests.exceptions.RequestException:
        pass
    
    return emails

# Function to get emails from Hunter.io API
def hunter_io_emails(domain, api_key):
    emails = set()
    if not api_key:
        return emails

    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'data' in data and 'emails' in data['data']:
            for email_entry in data['data']['emails']:
                emails.add(email_entry['value'])
    except requests.exceptions.RequestException:
        pass

    return emails

# Function to perform Google search and process each result
def google_search_and_scan(query, num_results, hunter_api_key):
    smtp_servers_found = []
    
    print(f"[*] Searching Google with query: '{query}' for {num_results} results...\n")
    for result in search(query, num_results=num_results):
        parsed_url = urlparse(result)

        # Ensure we have a valid domain
        if not parsed_url.netloc:
            print(f"[-] Skipping invalid result: {result}")
            continue

        domain = parsed_url.netloc
        print(f"[*] Checking {domain} for open SMTP ports...")

        open_ports = check_smtp_port(domain)

        if open_ports:
            print(f"[+] Open SMTP ports found on {domain}: {open_ports}")

            # Collect emails from crawling and Hunter.io
            site_emails = extract_emails(result)
            hunter_emails = hunter_io_emails(domain, hunter_api_key)

            all_emails = site_emails.union(hunter_emails)

            if all_emails:
                print(f"   [*] Emails found on {domain}: {all_emails}")
            else:
                print(f"   [-] No emails found on {domain}.")

            smtp_servers_found.append((domain, open_ports, all_emails))
        else:
            print(f"[-] No open SMTP ports found on {domain}.")
        
        time.sleep(2)  # Avoid rate limits
    
    return smtp_servers_found

if __name__ == "__main__":
    query = input("Enter your search query for Google (e.g., 'smtp open port'): ")
    num_results = int(input("Enter the number of results to scan (e.g., 10): "))
    hunter_api_key = input("Enter your Hunter.io API key (or leave blank to skip): ").strip()

    smtp_servers = google_search_and_scan(query, num_results, hunter_api_key)

    print("\n[*] Scan complete. Summary:")
    for domain, open_ports, emails in smtp_servers:
        print(f"\nDomain: {domain}")
        print(f"Open SMTP Ports: {open_ports}")
        if emails:
            print(f"Emails found: {emails}")
        else:
            print("No emails found.")
