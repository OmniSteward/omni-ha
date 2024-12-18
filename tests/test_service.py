import os
from homeassistant_api import Client

if __name__ == "__main__":
    url = os.getenv("HA_URL")
    token = os.getenv("HA_TOKEN")
    client = Client(f'{url}/api', token)

    for domain_name, domain in client.get_domains().items():
        # print(domain_name)
        if domain_name == 'select':
            print(domain)
            services = domain.services
            for service_name, service in services.items():
                print(service.service_id, service)