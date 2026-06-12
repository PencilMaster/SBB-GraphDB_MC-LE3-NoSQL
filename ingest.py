import pandas as pd
from scipy.spatial import cKDTree
from neo4j import GraphDatabase

def generate_graph_data(csv_path):
    print("Loading nodes...")
    # Read CSV, strictly extracting required fields
    df = pd.read_csv(csv_path, usecols=['xtf_id', 'Name', 'E', 'N'], low_memory=False)
    
    # Drop rows lacking spatial integrity
    nodes_df = df.dropna(subset=['xtf_id', 'E', 'N']).copy()
    nodes_df['Name'] = nodes_df['Name'].fillna('Unknown')
    
    # Cast coordinates to numeric
    nodes_df['E'] = pd.to_numeric(nodes_df['E'], errors='coerce')
    nodes_df['N'] = pd.to_numeric(nodes_df['N'], errors='coerce')
    nodes_df = nodes_df.dropna(subset=['E', 'N'])

    coords = nodes_df[['E', 'N']].values
    node_ids = nodes_df['xtf_id'].values
    names = nodes_df['Name'].values

    print("Computing KD-Tree topology...")
    # The first nearest neighbor is the point itself (distance 0)
    k = 5
    tree = cKDTree(coords)
    distances, indices = tree.query(coords, k=k)

    edges = []
    nodes = []
    
    for i in range(len(node_ids)):
        source_id = node_ids[i]
        nodes.append({
            'id': source_id,
            'name': names[i],
            'e': coords[i][0],
            'n': coords[i][1]
        })
        
        # Iterate over neighbors, skipping j=0 (self)
        for j in range(1, k):
            # cKDTree returns infinity/out-of-bounds index if less than k neighbors exist
            if indices[i, j] < len(node_ids): 
                target_id = node_ids[indices[i, j]]
                dist = distances[i, j]
                edges.append({
                    'source': source_id,
                    'target': target_id,
                    'distance': float(round(dist, 2))
                })

    print(f"Generated {len(nodes)} nodes and {len(edges)} directional edges.")
    return nodes, edges

def ingest_to_neo4j(nodes, edges):
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=None)

    def create_constraints(tx):
        tx.run("CREATE CONSTRAINT stop_id IF NOT EXISTS FOR (s:Stop) REQUIRE s.id IS UNIQUE")

    def insert_nodes(tx, batch):
        query = """
        UNWIND $batch AS row
        CREATE (n:Stop {id: row.id, name: row.name, e: row.e, n: row.n})
        """
        tx.run(query, batch=batch)

    def insert_edges(tx, batch):
        query = """
        UNWIND $batch AS row
        MATCH (source:Stop {id: row.source})
        MATCH (target:Stop {id: row.target})
        CREATE (source)-[r:CONNECTED_TO {distance: row.distance}]->(target)
        """
        tx.run(query, batch=batch)

    batch_size = 10000
    with driver.session() as session:
        print("Purging existing graph data...")
        # Auto-commit transaction for memory-safe batched deletion
        session.run("MATCH (n) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS")

        print("Applying schema constraints...")
        session.execute_write(create_constraints)
        
        print("Ingesting nodes...")
        for i in range(0, len(nodes), batch_size):
            session.execute_write(insert_nodes, nodes[i:i+batch_size])
            print(f"  Inserted {min(i+batch_size, len(nodes))}/{len(nodes)} nodes")
            
        print("Ingesting edges...")
        for i in range(0, len(edges), batch_size):
            session.execute_write(insert_edges, edges[i:i+batch_size])
            print(f"  Inserted {min(i+batch_size, len(edges))}/{len(edges)} edges")
            
    driver.close()
    print("Graph database ingestion fully complete.")

if __name__ == "__main__":
    nodes, edges = generate_graph_data('data/df_haltekante_clean.csv')
    ingest_to_neo4j(nodes, edges)
