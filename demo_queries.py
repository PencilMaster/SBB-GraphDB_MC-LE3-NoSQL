from neo4j import GraphDatabase

def run_validation_queries():
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=None)

    def create_index(tx):
        # Enforces O(1) lookups for node names instead of O(N) label scans.
        tx.run("CREATE INDEX stop_name_idx IF NOT EXISTS FOR (s:Stop) ON (s.name)")

    def project_graph(tx):
        # Drop existing projection to ensure idempotency
        tx.run("CALL gds.graph.drop('transitGraph', false) YIELD graphName")
        
        # Project topology and distance vectors into memory
        query = """
        CALL gds.graph.project(
            'transitGraph',
            'Stop',
            'CONNECTED_TO',
            { relationshipProperties: 'distance' }
        ) YIELD nodeCount, relationshipCount
        RETURN nodeCount, relationshipCount
        """
        return tx.run(query).single()

    def query_dijkstra(tx):
        # First, in Neo4j in the browser do:
        #   1. Click settings in bottom left and uncheck "Connect result nodes" (ONLY UNCHECK FOR DIJKSTRA QUERIES, THIS HIDES NOT RELEVANT EDGES).
        #   2. Execute: MATCH (source:Stop)-[r:CONNECTED_TO]->(target:Stop)
        #               WHERE source.e > 2600000 AND source.e < 2610000 
        #                   AND source.n > 1145000 AND source.n < 1160000
        #               RETURN source, r, target 
        # Then pick two of them and assign them to start.name and end.name.
        # Then the absolute shortest weighted route is computed.
        query = """
        MATCH (start:Stop) WHERE start.name = 'Adelboden, Schreiner Bärtschi'
        MATCH (end:Stop) WHERE end.name = 'Lenk, Gütsch'
        CALL gds.shortestPath.dijkstra.stream('transitGraph', {
            sourceNode: start,
            targetNode: end,
            relationshipWeightProperty: 'distance'
        })
        YIELD totalCost, path
        RETURN start.name AS start_node, end.name AS end_node, 
               totalCost AS total_distance, length(path) AS hops,
               [n in nodes(path) | n.name] AS route
        """
        return tx.run(query).single()

    with driver.session() as session:
        print("Applying schema optimizations...")
        session.execute_write(create_index)

        print("Projecting graph into RAM...")
        stats = session.execute_write(project_graph)
        print(f"  Projected {stats['nodeCount']} nodes and {stats['relationshipCount']} edges.")

        print("\nExecuting Dijkstra Pathfinding...")
        path = session.execute_read(query_dijkstra)
        if path:
            print(f"  Optimal Route: {path['start_node']} -> {path['end_node']}")
            print(f"  Geographic Distance: {round(path['total_distance'], 2)} meters")
            print(f"  Topology: {' -> '.join(path['route'])}")
        else:
            print("  Execution failed. Strict string equality matched zero nodes.")

    driver.close()

if __name__ == "__main__":
    # SPATIAL BOUNDING BOX REFERENCE (Swiss LV95 Coordinates)
    # The dataset exists strictly within these terrestrial boundaries:
    # MIN source.e: 2486179.44405  |  MAX source.e: 2832003.56366
    # MIN source.n: 1076165.94071  |  MAX source.n: 1294155.1313
    #
    # Execute the following window query in the Neo4j Browser to extract local clusters and pick two names for Dijkstra above:
    #
    # // Extracts a clean, un-truncated spatial cluster within a specific coordinate window
    # MATCH (source:Stop)-[r:CONNECTED_TO]->(target:Stop)
    # WHERE source.e > 2600000 AND source.e < 2610000 
    #   AND source.n > 1145000 AND source.n < 1160000
    # RETURN source, r, target 
    # LIMIT 400
    
    run_validation_queries()