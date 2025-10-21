import sys
from dbconnection import DBConnection
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the database connection with your config
db = DBConnection(
    host=os.getenv("DB_HOST", "107.173.146.16"),
    user=os.getenv("DB_USER", "acorn_user"),
    password=os.getenv("DB_PASSWORD", "Acorn_hr2025"),
    database=os.getenv("DB_NAME", "acorn_hr"),
    port=int(os.getenv("DB_PORT", "3306"))
)

def check_database_connectivity():
    """
    Comprehensive database connectivity check.
    - Tests connection
    - Tests a simple query (SELECT 1)
    - Tests fetching data from a sample table (e.g., 'employee' - adjust if needed)
    Returns a dict with status and details.
    """
    check_results = {
        'overall_status': 'failed',
        'details': []
    }
    
    try:
        # Step 1: Test basic connection
        print("Step 1: Testing basic connection...")
        db.connect()
        if db.connection and db.connection.is_connected():
            check_results['details'].append({'step': 'connection', 'status': 'success', 'message': 'Connected successfully'})
        else:
            raise Exception("Connection failed or not connected")
        
        # Step 2: Test simple query (SELECT 1)
        print("Step 2: Testing simple query...")
        test_query = "SELECT 1 as test_value"
        result = db.fetch_data(test_query)
        if result and result[0][0] == 1:
            check_results['details'].append({'step': 'simple_query', 'status': 'success', 'message': 'Simple query executed successfully'})
        else:
            raise Exception("Simple query failed or returned unexpected result")
        
        # Step 3: Test data fetch from a real table (e.g., count employees)
        print("Step 3: Testing data fetch...")
        data_query = "SELECT COUNT(*) as employee_count FROM employee"  # Adjust table if 'employee' doesn't exist
        data_result = db.fetch_data(data_query)
        if data_result:
            count = data_result[0][0]
            check_results['details'].append({'step': 'data_fetch', 'status': 'success', 'message': f'Data fetch successful. Employee count: {count}'})
        else:
            raise Exception("No data returned from table query")
        
        # All steps passed
        check_results['overall_status'] = 'success'
        print("\n✅ Database connectivity check PASSED!")
        
    except Exception as e:
        error_msg = f"Step failed: {str(e)}"
        check_results['details'].append({'step': 'error', 'status': 'failed', 'message': error_msg})
        print(f"\n❌ Database connectivity check FAILED: {error_msg}")
    
    finally:
        # Close connection if open
        try:
            db.disconnect()  # Use disconnect() as per your DBConnection class
        except:
            pass
    
    return check_results

if __name__ == "__main__":
    # Run the check
    results = check_database_connectivity()
    
    # Print summary
    print("\n=== SUMMARY ===")
    print(f"Overall Status: {results['overall_status'].upper()}")
    for detail in results['details']:
        status_emoji = "✅" if detail['status'] == 'success' else "❌"
        print(f"{status_emoji} {detail['step']}: {detail['message']}")
    
    # Exit with code (0 success, 1 failed) for scripting
    sys.exit(0 if results['overall_status'] == 'success' else 1)
