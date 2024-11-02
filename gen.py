import re
import yaml
import os
import sys
from collections import defaultdict


class Column:
    def __init__(self, name, data_type, is_pk=False, is_fk=False):
        self.name = name
        self.data_type = data_type
        self.is_pk = is_pk
        self.is_fk = is_fk

class Table:
    def __init__(self, name):
        self.name = name
        self.columns = []
        self.joins_with = []

    def add_column(self, column):
        print(column.name)
        self.columns.append(column)

    def add_join(self, join):
        print(join.source_column, join.destination_column)
        self.joins_with.append(join)

class Join:
    def __init__(self, source, destination, source_column, destination_column, is_one_to_one):
        self.source = source
        self.destination = destination
        self.source_column = source_column
        self.destination_column = destination_column
        self.is_one_to_one = is_one_to_one


def parse_erdiagram_tailored(erdiagram):
    tables = {}
    joins = []
    lines = erdiagram.split('\n')
    
    # First pass: Process relationships
    for line in lines:
        line = line.strip()
        if '||' in line or 'o{' in line or '}|' in line:
            parts = line.split(':')
            if len(parts) == 2:
                relation, condition = parts
                relation_parts = relation.split()
                if len(relation_parts) == 3:
                    source, _, destination = relation_parts
                    reverse_relation = relation_parts[1] == '||--o{'
                    is_one_to_one = relation_parts[1] == '||--||'

                    join_condition = condition.strip().strip('"')
                    if '=' in join_condition:
                        source_part, destination_part = join_condition.split('=')
                        source_column = source_part.strip().split('.')[-1]
                        destination_column = destination_part.strip().split('.')[-1]
                        join = Join(destination, source, destination_column, source_column, is_one_to_one) if reverse_relation else Join(source, destination, source_column, destination_column, is_one_to_one)
                        joins.append(join)

    # Second pass: Process table definitions
    current_table = None
    for line in lines:
        line = line.strip()
        if line.endswith('{'):
            table_name = line[:-1].strip()
            current_table = Table(table_name)
            tables[table_name] = current_table
        elif line == '}':
            current_table = None
        elif current_table is not None and line:
            parts = line.split()
            if len(parts) >= 2:
                name = parts[1]
                data_type = parts[0]
                is_pk = 'PK' in parts[2:] if len(parts) > 2 else False
                is_fk = 'FK' in parts[2:] if len(parts) > 2 else False
                current_table.add_column(Column(name, data_type, is_pk, is_fk))

    # Add joins to corresponding tables
    for join in joins:
        if join.source in tables:
            tables[join.source].add_join(join)

    return tables, joins


def generate_table_tml(table):
    tml = {
        'table': {
            'name': f"{table.name}_CLAUDE",
            'db': 'TPCH5K',
            'schema': 'falcon_default_schema',
            'db_table': f"{table.name}_CLAUDE",
            'columns': []
        }
    }

    for column in table.columns:
        unique_name = f"{table.name} {column.name}"
        data_type = 'INT64'
        if column.data_type.lower() in ['int', 'integer', 'bigint']:
            data_type = 'INT64'
        elif column.data_type.lower() in ['float', 'double', 'decimal']:
            data_type = 'FLOAT'
        elif column.data_type.lower() in ['date']:
            data_type = 'DATE'
        else:
            data_type = 'VARCHAR'

        column_type = 'MEASURE' if column.data_type.lower() in ['int', 'float', 'decimal'] else 'ATTRIBUTE'

        if column.is_fk or column.is_pk:
            column_type = 'ATTRIBUTE'

        col_tml = {
            'name': unique_name,
            'db_column_name': column.name.upper(),
            'properties': {
                'column_type': column_type
            },
            'db_column_properties': {
                'data_type': data_type
            }
        }
        tml['table']['columns'].append(col_tml)

    if table.joins_with:
        tml['table']['joins_with'] = []
        for join in table.joins_with:
            join_tml = {
                'name': f"{table.name} {join.source_column} - {join.destination} {join.destination_column}",
                'destination': {'name': f"{join.destination}_CLAUDE"},
                'on': f"[{table.name}_CLAUDE::{table.name} {join.source_column}] = [{join.destination}_CLAUDE::{join.destination} {join.destination_column}]",
                'type': 'INNER'
            }
            if join.is_one_to_one:
                join_tml['is_one_to_one'] = True
            tml['table']['joins_with'].append(join_tml)

    return tml

def generate_worksheet_tml(tables, joins, worksheet):
    paths = process_joins(joins)

    worksheet_tml = {
        'worksheet': {
            'name': f"{worksheet}",
            'tables': [{'name': f"{table.name}_CLAUDE"} for table in tables.values()],
            'joins': [],
            'table_paths': [],
            'worksheet_columns': []
        }
    }

    for join in joins:
        worksheet_tml['worksheet']['joins'].append({
            'name': f"{join.source} {join.source_column} - {join.destination} {join.destination_column}",
            'source': f"{join.source}_CLAUDE",
            'destination': f"{join.destination}_CLAUDE",
            'type': 'INNER',
            'is_one_to_one': join.is_one_to_one
        })

    for i, table in enumerate(tables.values()):
        table_path = {
            'id': f"{table.name}_CLAUDE_{i+1}",
            'table': f"{table.name}_CLAUDE"
        }
        
        join_paths = paths[table.name]

        if join_paths and join_paths[0]:
            table_path['join_path'] = [{'join': [f"{join.source} {join.source_column} - {join.destination} {join.destination_column}" for join in join_path]} for join_path in join_paths]
        
        worksheet_tml['worksheet']['table_paths'].append(table_path)

        for column in table.columns:
            unique_name = f"{table.name} {column.name}"
            worksheet_tml['worksheet']['worksheet_columns'].append({
                'name': unique_name,
                'column_id': f"{table.name}_CLAUDE_{i+1}::{unique_name}",
                'properties': {
                    'column_type': 'MEASURE' if column.data_type.lower() in ['int', 'float', 'decimal'] else 'ATTRIBUTE'
                }
            })
            if column.data_type.lower() in ['int', 'float', 'decimal']:
                worksheet_tml['worksheet']['worksheet_columns'][-1]['properties']['aggregation'] = 'SUM'

    worksheet_tml['worksheet']['properties'] = {
        'is_bypass_rls': False,
        'join_progressive': True
    }

    return worksheet_tml

def create_graph(joins):
    graph = defaultdict(list)
    nodes = set()

    for join in joins:
        nodes.add(join.source)
        nodes.add(join.destination)
        
        if join.is_one_to_one:
            graph[join.source].append((join.destination, join))
            graph[join.destination].append((join.source, join))
        else:
            graph[join.source].append((join.destination, join))

    return graph, nodes

def find_roots(graph, nodes):
    incoming_edges = set()
    for node in graph:
        for dest, _ in graph[node]:
            incoming_edges.add(dest)
    
    roots = nodes - incoming_edges
    return list(roots) if roots else [next(iter(nodes))]

def find_paths(graph, roots):
    paths = defaultdict(list)
    
    def dfs(node, current_path, visited):
        visited.add(node)
        paths[node].append(current_path)
        
        for neighbor, join in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, current_path + [join], visited.copy())
    
    for root in roots:
        dfs(root, [], set())
    
    return paths

def process_joins(joins):
    # Task 1: Create the graph
    graph, nodes = create_graph(joins)
    
    # Task 2: Find roots and paths from roots to each node
    roots = find_roots(graph, nodes)
    paths = find_paths(graph, roots)
    
    # Print the results
    print(f"Root nodes: {roots}")
    for node, node_paths in paths.items():
        print(f"\nPaths to {node}:")
        for path in node_paths:
            if not path:  # This is a root node
                print(f"  {node} (Root)")
            else:
                print(f"  Path: {' -> '.join([join.source for join in path] + [node])}")
                for join in path:
                    print(f"    {join.source} -> {join.destination} ({join.source_column} = {join.destination_column})")
        print()

    return paths

# Example usage:
# joins = [
#     Join("USER", "ORDER", "customer_id", "customer_id", False),
#     Join("ORDER", "ORDER_LINE", "order_id", "order_id", False),
#     Join("ORDER_LINE", "SKU", "product_id", "product_id", False),
#     Join("ORDER", "DATE", "order_date_id", "date_id", False),
#     Join("SKU", "DATE", "introduction_date_id", "date_id", False)
# ]


def save_tml_to_file(tml, filename):
    """Save TML content to a file."""
    with open(filename, 'w') as file:
        yaml.dump(tml, file, sort_keys=False)
    print(f"Saved TML to {filename}")


def generate_tml(erdiagram, worksheet ):
    # Read erDiagram from input file
    # with open(input_file, 'r') as file:
    #     erdiagram = file.read()

    # Parse erDiagram
    tables, joins = parse_erdiagram_tailored(erdiagram)

    # Initialize dictionary to store files
    generated_files = {}
    
    # Generate table TMLs
    for table_name, table in tables.items():
        tml = generate_table_tml(table)
        filename = f"{table_name}_table.tml"
        generated_files[filename] = tml
    
    # Generate worksheet TML
    worksheet_tml = generate_worksheet_tml(tables, joins, worksheet)
    worksheet_filename = f"{worksheet}_worksheet.tml"
    generated_files[worksheet_filename] = worksheet_tml
    
    return generated_files

# Optional: If you still want the ability to save to disk
def save_to_disk(generated_files, worksheet):
    """
    Save the generated files to disk in a directory.
    
    Args:
        generated_files (dict): Dictionary of filename: content pairs
        worksheet (str): Name of the worksheet (used for directory name)
    """
    output_dir = f"{worksheet}-tmls"
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, content in generated_files.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            f.write(content)