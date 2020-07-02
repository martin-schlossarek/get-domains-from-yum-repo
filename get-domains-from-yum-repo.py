import argparse
import gzip
import logging
import os
import requests
from urllib.parse import urlparse
from xml.etree import ElementTree

REPO_NS = "{http://linux.duke.edu/metadata/repo}"
COMMON_NS = "{http://linux.duke.edu/metadata/common}"
RPM_NS = "{http://linux.duke.edu/metadata/rpm}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


class Loader:
    def __init__(self):
        self.history_urls = []
        self.history_domains = []

    def add_history(self, response):
        urls = [response.url]

        for history in response.history:
            urls.append(history.url)

        for url in urls:
            domain = urlparse(url).netloc
            if url not in self.history_urls:
                self.history_urls.append(url)
            if domain not in self.history_domains:
                self.history_domains.append(domain)

    def load(self, url, head=False):
        logging.info(f"loading: {url}")
        if head:
            response = requests.head(url)
        else:
            response = requests.get(url)

        self.add_history(response)

        return response


class YumRepository:
    def __init__(self, url):
        self.url = url
        self.loader = Loader()

    def get_repomd_xml(self):
        response = self.loader.load(os.path.join(self.url, "repodata/repomd.xml"))
        return ElementTree.fromstring(response.text)

    def get_primary_xml(self, repomd_xml):
        primary_xml_url = repomd_xml.find(f"{REPO_NS}data[@type='primary']/{REPO_NS}location").attrib["href"]
        response = self.loader.load(os.path.join(self.url, primary_xml_url))
        return ElementTree.fromstring(gzip.decompress(response.content))

    def get_packages(self, primary_xml):
        packages = []
        for package in primary_xml.findall(f"{COMMON_NS}package/{COMMON_NS}location"):
            package_url = package.attrib["href"]
            self.loader.load(os.path.join(self.url, package_url), head=True)
            packages.append(package)
        return packages

    def get_domains(self):
        self.get_packages(self.get_primary_xml(self.get_repomd_xml()))

        print("Domains:")
        for domain in self.loader.history_domains:
            print(f"  {domain}")


def main():
    parser = argparse.ArgumentParser(description="Get all domains used in a specific yum repository")
    parser.add_argument("url", help="url to yum repository")
    parser.add_argument("-l", "--logging", action="store_true", help="enable logging")
    args = parser.parse_args()

    if args.logging:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.ERROR)

    repo = YumRepository(args.url)
    repo.get_domains()


if __name__ == "__main__":
    main()
