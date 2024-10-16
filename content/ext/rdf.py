import rdflib
import ipycytoscape as cy
import networkx as nx
import pandas as pd
import requests
from IPython.display import HTML
import urllib3

# Suppress the InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Funktionsdefinition für die Konvertierung von RDF zu NetworkX
def rdflib_to_networkx(rdf_graph):
    G = nx.DiGraph()  # Use Graph() if you want an undirected graph
    literal_counter = 0  # To ensure uniqueness for literals
    for subj, pred, obj in rdf_graph:
        
        # Handle subject
        if isinstance(subj, rdflib.URIRef):
            subj_str = rdf_graph.qname(subj)
            G.add_node(subj_str, node_type='URIRef')  # Mark it as a URIRef node
        elif isinstance(subj, rdflib.BNode):
            subj_str = f"_:bnode_{subj}"
            G.add_node(subj_str, node_type='BNode')  # Mark it as a blank node

        # Handle predicate
        if isinstance(pred, rdflib.URIRef):
            pred_str = rdf_graph.qname(pred)

        # Handle object
        if isinstance(obj, rdflib.URIRef):
            obj_str = rdf_graph.qname(obj)
            G.add_node(obj_str, node_type='URIRef')  # Mark it as a URIRef node
        elif isinstance(obj, rdflib.BNode):
            obj_str = f"_:bnode_{obj}"
            G.add_node(obj_str, node_type='BNode')  # Mark it as a blank node
        elif isinstance(obj, rdflib.Literal):
            # Create a unique identifier for the literal by appending a counter
            literal_id = f"Literal_{literal_counter}_{str(obj)}"
            literal_counter += 1
            obj_str = literal_id
            G.add_node(obj_str, label = str(obj), node_type='Literal')  # Mark it as a Literal node

        # Add the edge with the label as the predicate
        G.add_edge(subj_str, obj_str, label=pred_str)
    return G

# Funktionsdefinition, um einen TTL String zu parsen und als Graph zu plotten
def parse_and_plot(ttl_string):
    g = rdflib.Graph()
    g.parse(data = ttl_string)
    nx_graph = rdflib_to_networkx(g)
    plot = cy.CytoscapeWidget()
    plot.graph.add_graph_from_networkx(nx_graph, directed=True)

    style = [
        {
            'selector': 'node[node_type = "URIRef"]',
             'style': {
                'font-family': 'helvetica',
                'font-size': '12px',
                 'color': 'white',
                'text-outline-width': 2,
                'text-outline-color': '#0868ac',
                'background-color': '#0868ac',
                'content': 'data(id)',
                'text-valign': 'center'
             }
        },
        {
            'selector': 'node[node_type = "Literal"]',
             'style': {
                'font-family': 'helvetica',
                'font-size': '12px',
                 'color': 'white',
                'text-outline-width': 2,
                'text-outline-color': '#7bccc4',
                'background-color': '#7bccc4',
                'content': 'data(label)',
                'text-valign': 'center',
                'shape': 'rectangle'
             }
        },
        {
            'selector': 'node[node_type = "BNode"]',
             'style': {
                'background-color': 'grey',
                'width': '10',
                'height': '10'
             }
        },
        {
            'selector': 'edge.directed',
            'style': {
                'font-family': 'helvetica',
                'font-size': '12px',
                'label': 'data(label)',
                'color': 'white',
                'text-outline-width': 2,
                'text-outline-color': '#43a2ca',
                'background-color': '#43a2ca',
                'curve-style': 'bezier',
                'target-arrow-shape': 'triangle'
            }
        }
    ]
    
    plot.set_style(style)
    return plot

# Funktionsdefinition, um eine Query gegen eine lokale Turtle Datei auszuführen
def local_query(ttl_string, query_string):
    
    g = rdflib.Graph()
    g.parse(data = ttl_string)

    qres = g.query(query_string)

    df = pd.DataFrame(qres, columns=qres.vars)
    return df

# Funktionsdefinition, um eine SPARQL Query gegen einen SPARQL Endpoint auszuführen
def remote_query(query_string, store="L"):
    """
    Sends a SPARQL query to a SPARQL endpoint and returns the results as a pandas DataFrame.
    
    Parameters:
    - query_string: The SPARQL query string.
    - store: The URL of the SPARQL endpoint (triple store) or some predefined abbrevations.
    
    Returns:
    - A pandas DataFrame containing the query results.
    """
    # Define the headers for the request
    headers = {
        'Accept': 'application/sparql-results+json',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    # three Swiss triplestores
    if store == "F":
        address = 'https://fedlex.data.admin.ch/sparqlendpoint'
    elif store == "G":
        address = 'https://geo.ld.admin.ch/query'
    elif store == "L":
        address = 'https://ld.admin.ch/query'
    else:
        address = store

    # URL-encode the query parameters
    payload = {'query': query_string}
    
    # Send the request to the SPARQL endpoint
    response = requests.post(address, data=payload, headers=headers)

    # Ensure the response uses UTF-8 encoding
    response.encoding = 'utf-8'
    
    # Raise an exception if the request was not successful
    response.raise_for_status()
    
    # Parse the JSON response
    results = response.json()
    
    # Extract the variable names and the data
    columns = results['head']['vars']
    data = [
        {var: binding.get(var, {}).get('value') for var in columns}
        for binding in results['results']['bindings']
    ]
    
    # Create a pandas DataFrame from the data
    df = pd.DataFrame(data, columns=columns)

    # Convert columns to numeric datatype if possible
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except ValueError:
            pass  # Keeps the original data if conversion fails
    
    return df

# Funktionsdefinition, um ein DataFrame als Tabelle mit aktiven HTML Links anzuzeigen
def display_result(df):
    df = HTML(df.to_html(render_links=True, escape=False))
    display(df)