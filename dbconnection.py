import mysql.connector

class DBConnection:

    def __init__(self, host, user, password, database, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None

    def connect(self):
        try:
            # Establishing the connection
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port  
            )
            if self.connection.is_connected():
                print("Connected to MySQL database")
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            self.connection = None

    def disconnect(self):
        if self.connection.is_connected():
            self.connection.close()
            print("MySQL connection is closed")

    def execute_query(self, query, params=None):
        if self.connection and self.connection.is_connected():
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()
            cursor.close()

    def fetch_data(self, query, params=None):
        if self.connection and self.connection.is_connected():
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        return None