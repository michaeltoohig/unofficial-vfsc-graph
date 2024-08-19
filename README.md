# Unofficial VFSC Graph

This website reshapes public records from the Vanuatu Financial Services Commission (VFSC) and presents them visually as a graph allowing for analysis of shareholder and director connections.

![Unofficial VFSC Graph Landing Page](https://github.com/michaeltoohig/unofficial-vfsc-graph/blob/images/screenshot-landing-page.png?raw=true "Unofficial VFSC Graph Landing Page")

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
First, I intended to reduce load on my VPS by deciding the SQLite would be a fair choice for a small project.
Second, the crawler using Playwright is also a load on a small VPS so I intended to run it from a second machine.
Without an API on the webapp that meant I would keep a copy of the database locally and remote for the production service.
Changes to the graph database would then need to be copied to the production webapp for changes to be reflected on the website.
All because I didn't want to spin up an independent database service in this project.

I later found I needed a worker to write webapp usage stats to the SQLite database because it was making my pages load slowly when it was blocking the response.
Again, I am avoiding additional services such as an independent worker and message queue so I opted for a thread that runs in the Flask app and processes some DB writes without blocking the webapp response.
This became an issue during deployment as threads are a PITA with production WSGI web servers.
I also have to be careful with deployment now because I'm using a local queue which means I will be tied to only one process in production.

Although, I am happy with how it performs in development. 

So this is my current area of work and I may cave and add additional services and setup a more traditional project structure with additional services such as queue and worker service.

### Road Map

Future goals for completing the project are as follows:

 * [ ] Deployment
 * [ ] Custom base Docker image to reduce size of webapp image
   * drop nginx from container
 * [ ] Automated and gentle crawl schedule
   * [ ] Automated replacement of webapp graph db

However, my immediate goal is to refactor my background task thread into a worker process to get around deployment issues with my base docker image built on uWSGI which does not support threads as I need, or at least it doesn't perform as intended even when configured supposedly to use threads.

