# Swiss Public Transit Graph Database

A spatial graph database implementation modeling the Swiss public transit network using **Neo4j** and the **Graph Data Science (GDS)** library. This project calculates topological routing and weighted shortest paths (Dijkstra) between physical transit stops based on Swiss LV95 coordinate data.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Installation \& Setup](#installation--setup)
- [Usage](#usage)
  - [1. Data Ingestion](#1-data-ingestion)
  - [2. Analytical Queries](#2-analytical-queries)
- [Graph Exploration (Neo4j Browser)](#graph-exploration-neo4j-browser)
- [Teardown](#teardown)

## Prerequisites

Ensure your host system meets the following requirements:
* **Python 3.9+**
* **Docker Engine** & **Docker Compose** (For macOS Apple Silicon users, OrbStack or Docker Desktop is recommended).
* **Git**

## Project Structure

```text
.
├── data/
│   └── Betriebspunkt.csv         # Contains the stop-names
│   └── df_haltekante_clean.csv   # Raw Swiss transit coordinate data (LV95)
│   └── Haltekante.csv            # Used to filter out valid ids in "Betriebspunkt"
├── docker-compose.yml            # Neo4j & GDS container orchestration
├── ingest.py                     # KD-Tree topology generation and Neo4j ingestion
├── demo_queries.py               # GDS RAM projection and Dijkstra pathfinding
└── README.md                     # Project documentation
```

## Installation and Setup

Note: The "data_cleaning" script does not need to be run anymore, because it already generated "df_haltekante_clean.csv".
I just included it in the submission, because it was part of the data preparation step.

1. Clone the repository

```bash
git clone <your-repository-url>
cd <repository-directory>
```

2. Provision the Database Infrastructure
Spin up the Neo4j container. Upon first initialization, the daemon will automatically download and mount the required Graph Data Science (graph-data-science) plugin.

```bash
docker compose up -d
```

Verify the container is healthy by polling the HTTP port (Wait for a 200 OK response):

```bash
curl -I http://localhost:7474
```

3. Initialize Python Virtual Environment
To prevent dependency pollution, construct an isolated environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

4. Install Dependencies

```bash
pip install pandas scipy neo4j
```

## Usage

1. Data Ingestion
The ingestion script reads the raw coordinate data, drops incomplete rows, and mathematically constructs a local topology using a k-nearest neighbors (KNN) algorithm (k=5). It then streams the nodes and edges into Neo4j using memory-safe batch transactions.

```bash
python ingest.py
```
Expected Output: The console will log the generation of approximately 53,000 nodes and 159,000 directed edges, followed by bulk-insertion progress.

2. Analytical Queries
The validation script interacts with the Neo4j Graph Data Science engine to execute weighted pathfinding. It creates necessary schema indices, projects the database topology into RAM, and computes the absolute shortest spatial route using Dijkstra's algorithm.

```bash
python demo_queries.py
```
Expected Output: The script will print the optimal traversal route between two hardcoded nodes (e.g., Adelboden, Schreiner Bärtschi to Lenk, Gütsch) and the total accumulated geographic distance in meters.

## Graph Exploration (Neo4j Browser)

The database includes a web interface for visual exploration and ad-hoc Cypher querying.

1. Navigate to http://localhost:7474.
2. Directly click on "Connect" without changing any information.
3. Important Visual Setting: Before running pathfinding visualizers, click the Gear Icon (⚙) in the bottom left of the browser and uncheck "Connect result nodes". This prevents the UI from drawing unrequested background relationships.

### Useful Diagnostic Cypher Queries

**Geographic Window Extraction**
Render a clean, un-truncated spatial cluster within a specific Swiss coordinate bounding box:
```Cypher
MATCH (source:Stop)-[r:CONNECTED_TO]->(target:Stop)
WHERE source.e > 2600000 AND source.e < 2610000 
  AND source.n > 1145000 AND source.n < 1160000
RETURN source, r, target 
LIMIT 400
```

**Shortest Path Dijkstra Visualisation**
Here you can insert two stops into "startName" and "endName",
that you picked out from the "geographic window extraction" query.
```Cypher
:params {startName: "Adelboden, Schreiner Bärtschi", endName: "Lenk, Gütsch"}
MATCH (start:Stop {name: $startName})
MATCH (end:Stop {name: $endName})
CALL gds.shortestPath.dijkstra.stream('transitGraph', {
    sourceNode: start,
    targetNode: end,
    relationshipWeightProperty: 'distance'
})
YIELD path
RETURN path
```

To stop the database and clean up system resources, run:
```bash
docker compose down
deactivate
```