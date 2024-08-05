# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html


import scrapy
from itemloaders.processors import Compose, Identity, TakeFirst, MapCompose
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from datetime import datetime


def parse_date(date_str):
    if date_str:
        return datetime.strptime(date_str, "%d-%b-%Y")
    return None


def parse_datetime(datetime_str):
    if datetime_str:
        return datetime.strptime(datetime_str, "%d-%b-%Y %H:%M:%S")
    return None


def strip_name(name):
    if name:
        return name.strip()
    return None


def to_int(value):
    if value:
        return int(value)
    return None


class GeneralDetails(scrapy.Item):
    entity_type = scrapy.Field()
    entity_status = scrapy.Field()
    registration_date = scrapy.Field(input_processor=MapCompose(parse_date))
    reregistration_date = scrapy.Field(input_processor=MapCompose(parse_date))
    deregistration_date = scrapy.Field(input_processor=MapCompose(parse_date))
    annual_filing_month = scrapy.Field()


class CurrentAddress(scrapy.Item):
    address = scrapy.Field()
    start_date = scrapy.Field(input_processor=MapCompose(parse_date))


class FormerAddress(CurrentAddress):
    end_date = scrapy.Field(input_processor=MapCompose(parse_date))


class OfficeAddress(scrapy.Item):
    current = scrapy.Field()
    former = scrapy.Field(output_processor=Identity())


class PostalAddress(scrapy.Item):
    current = scrapy.Field()
    former = scrapy.Field(output_processor=Identity())


class Addresses(scrapy.Item):
    email_address = scrapy.Field()
    office_address = scrapy.Field()
    postal_address = scrapy.Field()
    local_office_address = scrapy.Field()
    local_postal_address = scrapy.Field()
    overseas_office_address = scrapy.Field()
    overseas_postal_address = scrapy.Field()


class CurrentAgent(scrapy.Item):
    agent_type = scrapy.Field(output_processor=TakeFirst())
    individual_name = scrapy.Field(input_processor=MapCompose(strip_name))
    residential_address = scrapy.Field()
    postal_address = scrapy.Field()
    entity_number = scrapy.Field()
    entity_name = scrapy.Field()
    entity_type = scrapy.Field()
    entity_address = scrapy.Field()
    appointed_date = scrapy.Field(input_processor=MapCompose(parse_date))


class FormerAgent(CurrentAgent):
    ceased_date = scrapy.Field(input_processor=MapCompose(parse_date))


class Agents(scrapy.Item):
    current = scrapy.Field(output_processor=Identity())
    former = scrapy.Field(output_processor=Identity())


class CurrentDirector(scrapy.Item):
    name = scrapy.Field(input_processor=MapCompose(strip_name))
    residential_address = scrapy.Field()
    postal_address = scrapy.Field()
    consent = scrapy.Field()
    entity_number = scrapy.Field()
    entity_name = scrapy.Field()
    entity_type = scrapy.Field()
    appointed_date = scrapy.Field(input_processor=MapCompose(parse_date))


class FormerDirector(CurrentDirector):
    ceased_date = scrapy.Field(input_processor=MapCompose(parse_date))


class Directors(scrapy.Item):
    current = scrapy.Field(output_processor=Identity())
    former = scrapy.Field(output_processor=Identity())


class CurrentShareholder(scrapy.Item):
    name = scrapy.Field(input_processor=MapCompose(strip_name))
    entity_number = scrapy.Field()
    entity_name = scrapy.Field()
    entity_type = scrapy.Field()
    address = scrapy.Field()
    appointed_date = scrapy.Field(input_processor=MapCompose(parse_date))


class FormerShareholder(CurrentShareholder):
    ceased_date = scrapy.Field(input_processor=MapCompose(parse_date))


class Shareholders(scrapy.Item):
    total_shares = scrapy.Field(input_processor=MapCompose(to_int))
    current = scrapy.Field(output_processor=Identity())
    former = scrapy.Field(output_processor=Identity())


class ShareAllocation(scrapy.Item):
    number_of_shares = scrapy.Field(input_processor=MapCompose(to_int))
    individual_name = scrapy.Field(input_processor=MapCompose(strip_name))
    entity_name = scrapy.Field(input_processor=MapCompose(strip_name))
    shareholder_type = scrapy.Field(output_processor=TakeFirst())
    name = scrapy.Field(output_processor=TakeFirst())


class Filing(scrapy.Item):
    filing_name = scrapy.Field()
    submitted_date = scrapy.Field(input_processor=MapCompose(parse_datetime))
    registered_date = scrapy.Field(input_processor=MapCompose(parse_datetime))


class Company(scrapy.Item):
    company_name = scrapy.Field(input_processor=MapCompose(strip_name))
    company_number = scrapy.Field()
    company_type = scrapy.Field()

    general_details = scrapy.Field()
    addresses = scrapy.Field()
    agents = scrapy.Field()
    directors = scrapy.Field()
    shareholders = scrapy.Field()
    shares = scrapy.Field(output_processor=Identity())
    filings = scrapy.Field(output_processor=Identity())


class DefaultItemLoader(ItemLoader):
    default_output_processor = TakeFirst()


def set_default_name(values, loader_context):
    # breakpoint()
    name = loader_context.get("name")
    entity_name = loader_context.get("entity_name")

    # Check if both name fields are empty
    if not name and not entity_name:
        return "Unknown"
    return name or entity_name


class ShareholderLoader(ItemLoader):
    default_output_processor = TakeFirst()

    # name_out = Compose(TakeFirst(), set_default_name)
    # entity_name_out = Compose(TakeFirst())
