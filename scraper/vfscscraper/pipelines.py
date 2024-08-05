# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import sqlite3
from itertools import chain

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy import signals
from scrapy.exceptions import DropItem

from vfscscraper.database import DataManager
from vfscscraper.items import Company


class VfscscraperPipeline:
    def process_item(self, item, spider):
        return item


class VfscCompanyPipeline:
    def process_item(self, item, spider):
        if isinstance(item, Company):
            if "addresses" in item:
                addresses = item["addresses"]
                if addresses.get("local_office_address") and bool(
                    addresses["local_office_address"]["current"]
                ):
                    addresses["office_address"] = addresses.pop("local_office_address")
                    addresses["postal_address"] = addresses.pop("local_postal_address")
                    addresses.pop("overseas_office_address")
                    addresses.pop("overseas_postal_address")
                elif bool(addresses["overseas_office_address"]["current"]):
                    addresses["office_address"] = addresses.pop(
                        "overseas_office_address"
                    )
                    addresses["postal_address"] = addresses.pop(
                        "overseas_postal_address"
                    )
                    addresses.pop("local_office_address")
                    addresses.pop("local_postal_address")
                else:
                    addresses["office_address"] = None
                    addresses["postal_address"] = None
            if "directors" in item:
                for director in chain(
                    item["directors"].get("current", []),
                    item["directors"].get("former", []),
                ):
                    if not director.get("name") and not director.get("entity_name"):
                        director["name"] = "UNKNOWN"
            if "shareholders" in item:
                item["total_shares"] = item["shareholders"]["total_shares"]
                for shareholder in chain(
                    item["shareholders"].get("current", []),
                    item["shareholders"].get("former", []),
                ):
                    if shareholder.get("entity_number"):
                        if shareholder["entity_number"] == " ":
                            shareholder["entity_number"] = ""
                    if not shareholder.get("name") and not shareholder.get(
                        "entity_name"
                    ):
                        shareholder["name"] = "UNKNOWN"
            else:
                item["total_shares"] = 0
            if "shares" in item:
                for share in item["shares"]:
                    if share.get("individual_name"):
                        share["shareholder_type"] = "individual"
                    elif share.get("entity_name"):
                        share["shareholder_type"] = "entity"
                    else:
                        share["shareholder_type"] = None
            if "agents" in item:
                for agent in chain(
                    item["agents"].get("current", []),
                    item["agents"].get("former", []),
                ):
                    if agent.get("individual_name"):
                        agent["agent_type"] = "individual"
                    elif agent.get("entity_name"):
                        agent["agent_type"] = "entity"
                    else:
                        agent["agent_type"] = None
        return item


class DataManagerPipeline:
    def __init__(self):
        self.data_manager = DataManager()
        self.session_id = None
        self.items_processed = 0
        self.has_errors = False

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signal=signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        self.session_id = self.data_manager.start_scraping_session()
        spider.logger.info(f"Started scraping session: {self.session_id}")

    def spider_closed(self, spider):
        status = "failed" if self.has_errors else "success"
        self.data_manager.end_scraping_session(
            self.session_id, self.items_processed, status
        )
        spider.logger.info(
            f"Ended scraping session: {self.session_id} with status: {status}"
        )

    def process_item(self, item, spider):
        try:
            spider.logger.info("Processing item: %s", item["company_number"])
            self.data_manager.update_item(item)
            self.items_processed += 1
            return item
        except Exception as e:
            self.has_errors = True
            error_message = f"Error processing item {item.get('company_number', 'unknown')}: {str(e)}"
            self.data_manager.record_failed_item(
                self.session_id, item.get("company_number", "unknown"), error_message
            )
            spider.logger.error(error_message)
            raise DropItem(error_message)
