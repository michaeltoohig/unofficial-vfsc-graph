import re
from enum import Enum
import scrapy

# from scrapy.loader import ItemLoader
from scrapy_playwright.page import PageMethod
from vfscscraper.items import (
    Agents,
    Company,
    CurrentAgent,
    CurrentShareholder,
    DefaultItemLoader,
    FormerAgent,
    FormerShareholder,
    GeneralDetails,
    Addresses,
    PostalAddress,
    OfficeAddress,
    FormerAddress,
    CurrentAddress,
    ShareAllocation,
    ShareholderLoader,
    Shareholders,
    Filing,
    CurrentDirector,
    FormerDirector,
    Directors,
)
from vfscscraper.spiders.utils import abort_request


class VfscCompanyStatus(Enum):
    REGISTERED = "registered"
    RECEIVERSHIP = "receivership"
    ADMINISTRATION = "administration"
    LIQUIDATION = "liquidation"
    DISSOLVED = "dissolved"
    REMOVED = "removed"
    AMALGAMATED = "amalgamated"
    CONTINUE_AS = "continueAs"


class VfscCompanyType(Enum):
    LOCAL = "L"
    OVERSEAS = "O"


class VfscSpider(scrapy.Spider):
    name = "vfsc"
    allowed_domains = ["vfsc.vu"]
    start_urls = ["https://vfsc.vu"]

    custom_settings = {
        "PLAYWRIGHT_ABORT_REQUEST": abort_request,
    }

    def __init__(
        self, search_term, company_status=None, company_type=None, *args, **kwargs
    ):
        super(VfscSpider, self).__init__(*args, **kwargs)
        self.search_term = search_term
        self.company_status = None
        if company_status is not None:
            self.company_status = VfscCompanyStatus(company_status)
        if company_type is not None:
            self.company_type = VfscCompanyType(company_type)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta=dict(
                    playwright=True,
                    playwright_include_page=True,
                    playwright_page_methods=[
                        PageMethod(
                            "wait_for_selector", 'a[data-rel="#appMainNavigation"]'
                        ),
                        PageMethod("click", 'a[data-rel="#appMainNavigation"]'),
                        PageMethod("wait_for_selector", "a.menu-vanuatucompanies"),
                        PageMethod("click", "a.menu-vanuatucompanies"),
                        PageMethod("wait_for_selector", "a.br-menu-registerItemSearch"),
                        PageMethod("click", "a.br-menu-registerItemSearch"),
                    ],
                ),
                callback=self.parse,
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        queries = [self.search_term]

        for query in queries:
            await self.search_query(page, query)
            async for item in self.parse_results(page, response):
                yield item

    async def search_query(self, page, query):
        # set query filter
        if self.company_status or self.company_type:
            await page.click("div.Advanced a")
            if self.company_status:
                await page.wait_for_selector("select#Status")
                await page.select_option("select#Status", self.company_status.value)
                await page.wait_for_timeout(2000)  # compensate for JS delay
            if self.company_type:
                await page.wait_for_selector("select#Discriminant")
                await page.select_option("select#Discriminant", self.company_type.value)
                await page.wait_for_timeout(2000)  # compensate for JS delay
        # make query
        await page.wait_for_selector("input[name='QueryString']")
        await page.fill("input[name='QueryString']", query)
        await page.click("button.appSubmitButton")
        await page.wait_for_selector("div.appSearchResults")

    async def parse_results(self, page, response):
        while True:
            result_count = 0

            while True:
                content = await page.content()
                response = scrapy.http.HtmlResponse(
                    url=response.url, body=content, encoding="utf-8"
                )

                results = response.css("div.appRepeaterRowContent")
                if not results or result_count >= len(results):
                    break

                try:

                    result_id = results[result_count].css("::attr(id)").get()
                    if result_id:
                        async for item in self.parse_detail(page, response, result_id):
                            yield item
                        await page.wait_for_selector("div.appRepeaterRowContent")
                except Exception:
                    self.logger.exception("Failed to parse_detail")
                finally:
                    result_count += 1

            next_page = response.css("div.appNext.pagination-item a").get()
            if next_page:
                await page.click("div.appNext.pagination-item a")
                await page.wait_for_timeout(1000)  # compensate for JS delay
                await page.wait_for_selector("div.appRepeaterRowContent")
            else:
                break

    async def parse_detail(self, page, response, result_id):
        await page.click(f"div#{result_id} a")
        await page.wait_for_selector("div.appEntityDetailsContent")

        content = await page.content()
        response = scrapy.http.HtmlResponse(
            url=response.url, body=content, encoding="utf-8"
        )

        async for item in self.parse_detail_page(page, response):
            yield item

        await page.click("a.appCancel")

    async def parse_detail_page(self, page, response):
        loader = DefaultItemLoader(item=Company(), response=response)

        # Extract company information
        company_info = response.css("div.companyContextBox .appAttrValue::text").get()
        if company_info:
            company_name_match = re.search(r"^(.*?)\s\(", company_info)
            company_number_match = re.search(r"\((\d+)\)", company_info)
            local_match = re.search(r"\[(.*?)\]", company_info)
            loader.add_value(
                "company_name",
                company_name_match.group(1) if company_name_match else None,
            )
            loader.add_value(
                "company_number",
                company_number_match.group(1) if company_number_match else None,
            )
            loader.add_value(
                "company_type", local_match.group(1) if local_match else None
            )

        try:
            async for item in self.parse_detail_page_tabs(loader, page, response):
                yield item
        except Exception as exc:
            company = loader.load_item()
            self.logger.error(
                f"Failed to scrape tabs in {company['company_name']} [{company['company_number']}]"
            )
            raise exc

    async def parse_detail_page_tabs(self, loader, page, response):
        tabs = response.css("ul.appTabs li a")
        for tab in tabs:
            tab_id = tab.css("::attr(id)").get()
            if tab_id:
                await page.click(f"#{tab_id}")
                await page.wait_for_timeout(1000)  # compensate for JS delay
                await page.wait_for_selector(f"div[aria-labelledby='{tab_id}']")

                # Refresh the content and response after clicking each tab
                content = await page.content()
                response = scrapy.http.HtmlResponse(
                    url=response.url, body=content, encoding="utf-8"
                )

                # Call the appropriate method to scrape data from the selected tab
                if "detailsTab" in tab_id:
                    general_details = self.scrape_general_details(response)
                    loader.add_value("general_details", general_details)
                elif "addressesTab" in tab_id:
                    addresses = self.scrape_addresses(response)
                    loader.add_value("addresses", addresses)
                elif "directorsTab" in tab_id:
                    directors = self.scrape_directors(response)
                    loader.add_value("directors", directors)
                elif "shareholdingTab" in tab_id:
                    shareholders = self.scrape_shares_shareholders(response)
                    loader.add_value("shareholders", shareholders)
                elif "bundleAllocationTab" in tab_id:
                    shares = self.scrape_share_allocations(response)
                    loader.add_value("shares", shares)
                elif "filings" in tab_id:
                    filings = self.scrape_filings(response)
                    loader.add_value("filings", filings)
                elif "acceptSopTab" in tab_id:
                    agents = self.scrape_agents(response)
                    loader.add_value("agents", agents)

        yield loader.load_item()

    def scrape_general_details(self, response):
        content = response.css("div.appTabSelected")
        general_details_loader = DefaultItemLoader(
            item=GeneralDetails(), selector=content
        )
        general_details_loader.add_css(
            "entity_type", "div.EntityTypeLongDescription .appAttrValue::text"
        )
        general_details_loader.add_css(
            "entity_status", "div.Status .appAttrValue::text"
        )
        general_details_loader.add_css(
            "registration_date",
            "div.RegistrationDate .appAttrValue span[aria-hidden='true']::text",
        )
        general_details_loader.add_css(
            "reregistration_date",
            "div.ReregistrationDate .appAttrValue span[aria-hidden='true']::text",
        )
        general_details_loader.add_css(
            "deregistration_date",
            "div.DeregistrationDate .appAttrValue span[aria-hidden='true']::text",
        )
        general_details_loader.add_css(
            "annual_filing_month", "div.AnnualFilingMonth .appAttrValue::text"
        )
        return general_details_loader.load_item()

    def scrape_addresses(self, response):
        content = response.css("div.appTabSelected")
        addresses_loader = DefaultItemLoader(item=Addresses(), selector=content)
        addresses_loader.add_css(
            "email_address", "div.EntityEmailAddresses .appAttrValue::text"
        )

        ## Overseas Addresses
        overseas_office_selector = content.css(
            "div.brViewOverseasCompany-tabsBox-addressesTab-ppobBox"
        )
        overseas_office_address = self.scrape_office_addresses(overseas_office_selector)
        addresses_loader.add_value("overseas_office_address", overseas_office_address)
        overseas_postal_selector = content.css(
            "div.brViewOverseasCompany-tabsBox-addressesTab-afcBox-addressForCommunicationPostal"
        )
        overseas_postal_address = self.scrape_postal_addresses(overseas_postal_selector)
        addresses_loader.add_value("overseas_postal_address", overseas_postal_address)

        # Local Addresses
        local_office_selector = content.css(
            "div.brViewLocalCompany-tabsBox-addressesTab-roaBox"
        )
        local_office_address = self.scrape_office_addresses(local_office_selector)
        addresses_loader.add_value("local_office_address", local_office_address)
        local_postal_selector = content.css(
            "div.brViewLocalCompany-tabsBox-addressesTab-afcBox-addressForCommunicationPostal"
        )
        local_postal_address = self.scrape_postal_addresses(local_postal_selector)
        addresses_loader.add_value("local_postal_address", local_postal_address)
        return addresses_loader.load_item()

    def scrape_office_addresses(self, selector):
        loader = DefaultItemLoader(item=OfficeAddress(), selector=selector)

        current_roa_section = selector.css("div.Current")
        current_loader = DefaultItemLoader(
            item=CurrentAddress(), selector=current_roa_section
        )
        current_loader.add_css("address", "div.address .appAttrValue::text")
        current_loader.add_css(
            "start_date",
            "div.StartDate .appAttrValue span[aria-hidden='true']::text",
        )
        loader.add_value("current", current_loader.load_item())

        former_roa_list = []
        former_roa_items = selector.css("div.appHide div.appRepeaterRowContent")
        for item in former_roa_items:
            former_loader = DefaultItemLoader(item=FormerAddress(), selector=item)
            former_loader.add_css(
                "start_date",
                "div.StartDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_loader.add_css(
                "end_date", "div.EndDate .appAttrValue span[aria-hidden='true']::text"
            )
            former_loader.add_css("address", "div.address .appAttrValue::text")
            former_roa_list.append(former_loader.load_item())
        loader.add_value("former", former_roa_list)

        return loader.load_item()

    def scrape_postal_addresses(self, selector):
        loader = DefaultItemLoader(item=PostalAddress(), selector=selector)

        current_postal_address_section = selector.css("div.Current")
        current_loader = DefaultItemLoader(
            item=CurrentAddress(), selector=current_postal_address_section
        )
        current_loader.add_css("address", "div.postal .appAttrValue::text")
        current_loader.add_css(
            "start_date", "div.StartDate .appAttrValue span[aria-hidden='true']::text"
        )
        loader.add_value("current", current_loader.load_item())

        former_postal_address_list = []
        former_postal_address_items = selector.css(
            "div.appHide div.appRepeaterRowContent"
        )
        for item in former_postal_address_items:
            former_loader = DefaultItemLoader(item=FormerAddress(), selector=item)
            former_loader.add_css(
                "start_date",
                "div.StartDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_loader.add_css(
                "end_date", "div.EndDate .appAttrValue span[aria-hidden='true']::text"
            )
            former_loader.add_css("address", "div.postal .appAttrValue::text")
            former_postal_address_list.append(former_loader.load_item())
        loader.add_value("former", former_postal_address_list)

        return loader.load_item()

    def scrape_agents(self, response):
        content = response.css("div.appTabSelected")
        loader = DefaultItemLoader(item=Agents(), selector=content)

        current_agent_list = []
        current_agent_items = content.css("div.Current div.appRepeaterRowContent")
        for item in current_agent_items:
            current_loader = DefaultItemLoader(item=CurrentAgent(), selector=item)
            current_loader.add_css(
                "individual_name", "div.individualName .appAttrValue::text"
            )
            current_loader.add_css(
                "residential_address", "div.appPhysicalAddress .appAttrValue::text"
            )
            current_loader.add_css(
                "postal_address", "div.appPostalAddress .appAttrValue::text"
            )

            current_loader.add_css(
                "entity_number", "div.EntityNameOrNumber .appAttrValue::text"
            )
            current_loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            current_loader.add_css("entity_type", "div.EntityType .appAttrValue::text")
            current_loader.add_css(
                "entity_address",
                "div.EntityRolePhysicalAddresses .appAttrValue::text",
            )
            current_loader.add_css(
                "appointed_date",
                "div.AppointedDate .appAttrValue span[aria-hidden='true']::text",
            )
            current_agent_list.append(current_loader.load_item())
        loader.add_value("current", current_agent_list)

        former_agent_list = []
        former_agent_items = content.css("div.appHide div.appRepeaterRowContent")
        for item in former_agent_items:
            former_loader = DefaultItemLoader(item=FormerAgent(), selector=item)
            former_loader.add_css(
                "individual_name", "div.individualName .appAttrValue::text"
            )
            former_loader.add_css(
                "residential_address", "div.appPhysicalAddress .appAttrValue::text"
            )
            former_loader.add_css(
                "postal_address", "div.appPostalAddress .appAttrValue::text"
            )
            former_loader.add_css(
                "entity_number", "div.EntityNameOrNumber .appAttrValue::text"
            )
            former_loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            former_loader.add_css("entity_type", "div.EntityType .appAttrValue::text")
            former_loader.add_css(
                "entity_address",
                "div.EntityRolePhysicalAddresses .appAttrValue::text",
            )
            former_loader.add_css(
                "appointed_date",
                "div.AppointedDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_loader.add_css(
                "ceased_date",
                "div.CeasedDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_agent_list.append(former_loader.load_item())
        loader.add_value("former", former_agent_list)

        return loader.load_item()

    def scrape_directors(self, response):
        content = response.css("div.appTabSelected")
        loader = DefaultItemLoader(item=Directors(), selector=content)

        current_director_items = content.css("div.Current div.appRepeaterRowContent")
        current_director_list = []
        for item in current_director_items:
            current_loader = DefaultItemLoader(item=CurrentDirector(), selector=item)
            current_loader.add_css("name", "div.individualName .appAttrValue::text")
            current_loader.add_css(
                "residential_address",
                "div.EntityRolePhysicalAddresses .appAttrValue::text",
            )
            current_loader.add_css(
                "postal_address", "div.EntityRolePostalAddresses .appAttrValue::text"
            )
            current_loader.add_css(
                "consent", "div.ConsentReceivedYn .appAttrValue::text"
            )

            current_loader.add_css(
                "entity_number", "div.EntityIdentifierAssoc .appAttrValue::text"
            )
            current_loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            current_loader.add_css("entity_type", "div.EntityType .appAttrValue::text")
            current_loader.add_css(
                "appointed_date",
                "div.AppointedDate .appAttrValue span[aria-hidden='true']::text",
            )
            current_director_list.append(current_loader.load_item())
        loader.add_value("current", current_director_list)

        former_director_items = content.css(
            "div.appExpandoChildren.appHide div.appRepeaterRowContent"
        )
        former_director_list = []
        for item in former_director_items:
            former_loader = DefaultItemLoader(item=FormerDirector(), selector=item)
            former_loader.add_css("name", "div.individualName .appAttrValue::text")
            former_loader.add_css(
                "residential_address",
                "div.EntityRolePhysicalAddresses .appAttrValue::text",
            )
            former_loader.add_css(
                "postal_address", "div.EntityRolePostalAddresses .appAttrValue::text"
            )
            former_loader.add_css(
                "consent", "div.ConsentReceivedYn .appAttrValue::text"
            )

            former_loader.add_css(
                "entity_number", "div.EntityIdentifierAssoc .appAttrValue::text"
            )
            former_loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            former_loader.add_css("entity_type", "div.EntityType .appAttrValue::text")
            former_loader.add_css(
                "appointed_date",
                "div.AppointedDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_director_list.append(former_loader.load_item())
        loader.add_value("former", former_director_list)

        return loader.load_item()

    def scrape_shares_shareholders(self, response):
        content = response.css("div.appTabSelected")
        loader = DefaultItemLoader(item=Shareholders(), selector=content)
        loader.add_css("total_shares", "div.TotalShares .appAttrValue::text")

        current_shareholder_items = content.css("div.Current div.appRepeaterRowContent")
        current_shareholder_list = []
        for item in current_shareholder_items:
            current_loader = ShareholderLoader(item=CurrentShareholder(), selector=item)

            current_loader.add_css("name", "div.individualName .appAttrValue::text")
            current_loader.add_css(
                "entity_number", "div.EntityNameOrNumber .appAttrValue::text"
            )
            current_loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            current_loader.add_css("entity_type", "div.EntityType .appAttrValue::text")
            current_loader.add_css(
                "address", "div.EntityRolePhysicalAddresses .appAttrValue::text"
            )
            current_loader.add_css(
                "appointed_date",
                "div.AppointedDate .appAttrValue span[aria-hidden='true']::text",
            )
            current_shareholder_list.append(current_loader.load_item())
        loader.add_value("current", current_shareholder_list)

        former_shareholder_items = content.css("div.appHide div.appRepeaterRowContent")
        former_shareholder_list = []
        for item in former_shareholder_items:
            former_loader = ShareholderLoader(item=FormerShareholder(), selector=item)
            former_loader.add_css("name", "div.individualName .appAttrValue::text")
            former_loader.add_css(
                "entity_number", "div.EntityNameOrNumber .appAttrValue::text"
            )
            former_loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            former_loader.add_css("entity_type", "div.EntityType .appAttrValue::text")
            former_loader.add_css(
                "address", "div.EntityRolePhysicalAddresses .appAttrValue::text"
            )
            former_loader.add_css(
                "appointed_date",
                "div.AppointedDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_loader.add_css(
                "ceased_date",
                "div.CeasedDate .appAttrValue span[aria-hidden='true']::text",
            )
            former_shareholder_list.append(former_loader.load_item())
        loader.add_value("former", former_shareholder_list)

        return loader.load_item()

    def scrape_share_allocations(self, response):
        content = response.css("div.appTabSelected")
        share_allocation_items = content.css("div.appRepeaterRowContent")
        share_allocation_list = []
        for item in share_allocation_items:
            loader = DefaultItemLoader(item=ShareAllocation(), selector=item)
            loader.add_css("number_of_shares", "div.NumberOfUnits .appAttrValue::text")
            loader.add_css("individual_name", "div.individualName .appAttrValue::text")
            loader.add_css("entity_name", "div.EntityName .appAttrValue::text")
            share_allocation_list.append(loader.load_item())
        return share_allocation_list

    def scrape_filings(self, response):
        content = response.css("div.appTabSelected")
        filing_items = content.css("div.appRepeaterRowContent")
        filing_list = []
        for item in filing_items:
            loader = DefaultItemLoader(item=Filing(), selector=item)
            loader.add_css("filing_name", "div.appFilingName span::text")
            loader.add_css(
                "submitted_date",
                "div.appFilingSubmitted span[aria-hidden='true']::text",
            )
            loader.add_css(
                "registered_date", "div.appFilingEnd span[aria-hidden='true']::text"
            )
            filing_list.append(loader.load_item())
        return filing_list
