# Unofficial VFSC Graph

This website reshapes public records from the Vanuatu Financial Services Commission (VFSC) and presents them visually as a graph allowing for analysis of shareholder and director connections.

![Unofficial VFSC Graph Landing Page](https://github.com/michaeltoohig/unofficial-vfsc-graph/blob/master/images/screenshot-landing-page.png?raw=true "Unofficial VFSC Graph Landing Page")

Built using the following technologies:
 * Playwright - For headless browser automation
 * Scrapy - For extracting and processing data from websites
 * Flask - A micro web framework
 * SQLite - A small database engine
 * NetworkX - For network analysis (backend)
 * Cytoscape.js - A graph-theory library for visualization (frontend)


### Unofficial Nature

This website is an unofficial source of public data and is not affiliated with or endorsed by the Vanuatu Financial Services Commission (VFSC).
The data presented on this website is gathered from public records and is provided "as-is" without any warranties of any kind, either express or implied.
There are no guarantees of the accuracy, completeness, or reliability of the information.

The official records are available publicly at [https://vfsc.vu](https://vfsc.vu).
Always consult the VFSC for up-to-date and correct information.

## Development

The project can be built and run via Docker.

```sh
docker compose build
docker compose up -d
```

At the moment there is no automated web crawling schedule so the spider needs to be manually run to gather new information.

```sh
docker compose exec scraper poetry run scrapy crawl vfsc -a search_term=$TERM
```

This will update the current state of the graph as well as record history of changes.

Because the next development milestone includes automating a crawling schedule, the database on the webapp is not currently updated when you manually crawl.
The database populated by the crawl will need to be copied to the shared `data` directory where then the webapp can read the graph.

```sh
cp scraper/current_state.db data/graph.db
docker compose restart
```

This design decision was based on limitations of my VPS and may change in the future.
The design as it is now allows for scraping to be performed independently on a different machine and at a later date the webapp can be provided an updated graph.

### Design Decisions

I made some odd design decisions around database access and limiting external services.

First, I intended to reduce load on my VPS by deciding that SQLite would be a fair choice for such a small project.
Second, the crawler using Playwright is also a load on a small VPS so I intended to run it from a second machine.
Without an API on the webapp that meant I would keep a copy of the database for the crawler and for the production webapp service.
Changes to the graph database would then need to be copied to the production webapp for changes to be reflected on the website.
All because I didn't want to spin up an independent database service for this project.

I later found I needed a worker to write webapp usage stats to the webapp SQLite database because it was making my pages load slowly when it was blocking the response.
Again, I am avoiding additional services such as an independent worker and message queue so I opted for a thread that runs in the Flask app and processes database writes without blocking the webapp response.

### Road Map

Future goals for completing the project are as follows:

 * [x] Deployment (ansible & opentofu scripts)
 * [x] Custom base Docker image to reduce size of webapp image
   * [x] drop nginx from container
 * [ ] Automated and gentle crawl schedule
   * [ ] Automated replacement of webapp graph db

