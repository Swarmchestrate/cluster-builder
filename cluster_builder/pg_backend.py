import psycopg2
from config import pg_config  # Assuming pg_config is a dictionary or separate config file

class PGBackend:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=pg_config['host'],
                database=pg_config['database'],
                user=pg_config['user'],
                password=pg_config['password']
            )
            self.cursor = self.connection.cursor()
            print("PostgreSQL connection established.")
        except Exception as error:
            print(f"Error connecting to PostgreSQL: {error}")

    def create_table_for_cluster(self, cluster_name):
        try:
            table_name = f"cluster_{cluster_name}"
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                resource_type VARCHAR(255),
                resource_name VARCHAR(255),
                status VARCHAR(255),
                state JSONB
            );
            """
            self.cursor.execute(create_table_query)
            self.connection.commit()
            print(f"Table for cluster {cluster_name} created (if not exists).")
        except Exception as error:
            print(f"Error creating table for cluster {cluster_name}: {error}")

    def insert_state(self, cluster_name, resource_type, resource_name, status, state):
        try:
            table_name = f"cluster_{cluster_name}"
            insert_query = f"""
            INSERT INTO {table_name} (resource_type, resource_name, status, state)
            VALUES (%s, %s, %s, %s)
            """
            self.cursor.execute(insert_query, (resource_type, resource_name, status, state))
            self.connection.commit()
            print(f"State for {resource_name} inserted into {table_name}.")
        except Exception as error:
            print(f"Error inserting state into {table_name}: {error}")

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("PostgreSQL connection closed.")
