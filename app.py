# libraries

from flask import Flask, render_template, request, session, redirect, url_for, send_file, Response, jsonify
from datetime import datetime, date
from dbconnection import DBConnection
import os
import logging
from decimal import Decimal
from fpdf import FPDF
from tempfile import NamedTemporaryFile
from PIL import Image
import re
import imagehash
try:
    import pandas as pd
except ImportError as e:
    
    pd = None
from io import BytesIO
from dotenv import load_dotenv
from passlib.hash import bcrypt


# Configure logging for production
if os.getenv("FLASK_ENV") == "production":
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)

load_dotenv()

# Flask app configuration
app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key-for-development")
app.config['SESSION_COOKIE_SECURE'] = os.getenv("FLASK_ENV") == "production"  # HTTPS in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# initialize the database connection
db = DBConnection(
    host=os.getenv("DB_HOST", "107.173.146.16"),
    user=os.getenv("DB_USER", "acorn_user"),
    password=os.getenv("DB_PASSWORD", "Acorn_hr2025"),
    database=os.getenv("DB_NAME", "acorn_hr"),
    port=int(os.getenv("DB_PORT", "3306"))
)


try:
    db.connect()
    
except Exception as e:
    print(f"\n\033[0;31mDatabase connection failed: {e}\033[0m")
    print("Please check your database configuration and environment variables.")


# configure uploads folder path for Railway volume
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER_PATH', '/app/data/uploads')
# Fallback for local development
if not os.path.exists('/app/data'):
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# configure allowed extentions for image upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



""" Login Function """

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({"status": "healthy", "message": "AcornHR is running"}), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files from Railway volume"""
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

@app.route('/')
def login():
    
    return render_template('login.html')

@app.route('/signin', methods=['POST'])
def signin():
    
    email = request.form['email']
    password = request.form['password']

    

    # admin-access
    query = "SELECT * FROM admin WHERE Email = %s"
    admin_check = db.fetch_data(query, (email,))
    if admin_check:
        stored_hash = admin_check[0][2]  # assuming Password is 3rd column
        
        
        if bcrypt.verify(password, stored_hash):
            session['admin_id'] = admin_check[0][0]
            session['admin_name'] = admin_check[0][3] + " " + admin_check[0][4]
            
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'error': "Password is incorrect. Try again."})

    # employee-access
    query = "SELECT * FROM employee WHERE Email = %s"
    user_check = db.fetch_data(query, (email,))
    if user_check:
        stored_hash = user_check[0][2]  # assuming Password is 3rd column
        
        
        if bcrypt.verify(password, stored_hash):
            session['emp_id'] = user_check[0][0]
            session['emp_name'] = user_check[0][3] + " " + user_check[0][4]
            
            return jsonify({'success': True, 'redirect': url_for('emp_dashboard')})
        else:
            return jsonify({'success': False, 'error': "Password is incorrect. Try again."})

    return jsonify({'success': False, 'error': "Your account is not registered. Please contact Acorn HR for assistance."})


@app.route('/logout', methods=['GET'])
def logout():

    # clear the session data
    session.clear()

    # redirect the user to the login page
    return render_template('login.html')



""""Change employee Password Function"""

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'emp_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    emp_id = session['emp_id']

    # Fetch hashed password from DB
    query = "SELECT Password FROM employee WHERE EmpID = %s"
    result = db.fetch_data(query, (emp_id,))
    stored_hash = result[0][0]
    
    
    
    if not result or not bcrypt.verify(current_password, stored_hash):
        return jsonify({'error': 'Current password is incorrect. Try again.'})

    # Hash the new password and update
    new_hashed = bcrypt.hash(new_password)
    query = "UPDATE employee SET Password = %s WHERE EmpID = %s"
    db.execute_query(query, (new_hashed, emp_id))
    
    
    
    return jsonify({'success': True, 'message': 'Password updated successfully!'})

""""Change admin Password Function"""

@app.route('/change_admin_password', methods=['POST'])
def change_admin_password():
    if 'admin_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    admin_id = session['admin_id']

    # Fetch hashed password from DB
    query = "SELECT Password FROM admin WHERE AdminID = %s"
    result = db.fetch_data(query, (admin_id,))
    stored_hash = result[0][0]

    if not result or not bcrypt.verify(current_password, stored_hash):
        return jsonify({'error': 'Current password is incorrect. Try again.'})

    # Hash the new password and update
    new_hashed = bcrypt.hash(new_password)
    query = "UPDATE admin SET Password = %s WHERE AdminID = %s"
    db.execute_query(query, (new_hashed, admin_id))

    return jsonify({'success': True, 'message': 'Password updated successfully!'})



""" Employee Dashboard Function"""

@app.route('/emp_dashboard', methods=['GET', 'POST'])
def emp_dashboard():
    

    try:
        emp_id = session.get('emp_id')
        emp_name = session.get('emp_name')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching employee details'}), 500

    # fetch credit limits
    fuel_credit_query = "SELECT FuelCreditLimit FROM credit WHERE EmpID = %s"
    fuel_credit_limit = db.fetch_data(fuel_credit_query, (emp_id,))
    opd_credit_query = "SELECT OPDCreditLimit FROM credit WHERE EmpID = %s"
    opd_credit_limit = db.fetch_data(opd_credit_query, (emp_id,))
    fuel_credit_limit = fuel_credit_limit[0][0] if fuel_credit_limit else 0
    opd_credit_limit = opd_credit_limit[0][0] if opd_credit_limit else 0

    # fetch credit balance
    fuel_credit_query = "SELECT FuelCreditBalance FROM credit WHERE EmpID = %s"
    fuel_credit_balance = db.fetch_data(fuel_credit_query, (emp_id,))
    opd_credit_query = "SELECT OPDCreditBalance FROM credit WHERE EmpID = %s"
    opd_credit_balance = db.fetch_data(opd_credit_query, (emp_id,))
    fuel_credit_balance = fuel_credit_balance[0][0] if fuel_credit_balance else 0
    opd_credit_balance = opd_credit_balance[0][0] if opd_credit_balance else 0

    # fetch recent claims
    query = "SELECT ClaimID, DateOfRequest, Category, Amount, Status FROM claim WHERE EmpID = %s ORDER BY ClaimID DESC"
    claims = db.fetch_data(query, (emp_id,))

    recent_requests_query = """
        SELECT 
            claim.ClaimID, 
            employee.FirstName, 
            employee.LastName,
            claim.DateOfRequest, 
            claim.Amount, 
            claim.Category, 
            claim.EmpMessage,
            claimimage.Image,
            claim.Status, 
            admin.FirstName AS AdminFirstName,
            admin.LastName AS AdminLastName,
            admin.Email AS AdminEmail,
            admin.TpNo AS AdminTpNo, 
            claimapproval.DateOfApproval,
            claimapproval.AdminMessage
        FROM 
            claim
        JOIN 
            employee ON claim.EmpID = employee.EmpID
        JOIN 
            claimimage ON claim.ClaimID = claimimage.ClaimID
        LEFT JOIN 
            claimapproval ON claim.ClaimID = claimapproval.ClaimID
        JOIN
            admin ON claimapproval.AdminID = admin.AdminID
        WHERE 
            employee.EmpID = %s
        ORDER BY 
            claim.ClaimID DESC;

        """
    claim_details = db.fetch_data(recent_requests_query, (emp_id,))

    # store claim details in a dictionary
    claim_details_dict = {}
    for claim_id, first_name, last_name, date_of_request, amount, category, emp_message, image_url, status, admin_fname, admin_lname, admin_email, admin_tp, approval_date, admin_message in claim_details :
        if claim_id not in claim_details_dict:
            date_of_request = date_of_request.strftime('%d-%m-%Y') if date_of_request else None
            approval_date = approval_date.strftime('%d-%m-%Y') if approval_date else None  
            claim_details_dict[claim_id] = {
                'ClaimID': claim_id,
                'DateOfRequest': date_of_request,
                'Amount': amount,
                'Category': category,
                'Status': status,
                'EmpMessage': emp_message,
                'Employee': {
                    'FirstName': first_name,
                    'LastName': last_name,
                },
                'Images': [],
                'Admin': {
                    'FirstName': admin_fname,
                    'LastName': admin_lname,
                    'Email': admin_email,
                    'TpNo': admin_tp
                },
                'Approval': {
                    'DateOfApproval': approval_date,
                    'AdminMessage': admin_message
                }
            }
        if image_url:
            claim_details_dict[claim_id]['Images'].append(image_url)

    return render_template(
        'emp_dashboard.html',
        emp_name=emp_name,
        fuel_credit_limit=fuel_credit_limit,
        opd_credit_limit=opd_credit_limit,
        fuel_credit_balance=fuel_credit_balance,
        opd_credit_balance=opd_credit_balance,
        claims=claims,
        claim_details_dict=claim_details_dict 
    )

@app.route('/delete_claim/<int:claim_id>', methods=['DELETE'])
def delete_claim(claim_id):
    

    try:
        emp_id = session.get('emp_id')
        
        # fetch claim details
        query = "SELECT Category, Amount FROM claim WHERE ClaimID = %s"
        claim_data = db.fetch_data(query, (claim_id,))
        category = claim_data[0][0]
        amount = claim_data[0][1]
            
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500

    try:
        # delete associated claim images
        delete_images_query = "DELETE FROM claimimage WHERE ClaimID = %s"
        db.execute_query(delete_images_query, (claim_id,))

        if category == 'Fuel':
            update_balance_query = """
                UPDATE credit
                SET FuelCreditBalance = FuelCreditBalance + %s
                WHERE EmpID = %s
            """
        elif category == 'OPD':
            update_balance_query = """
                UPDATE credit
                SET OPDCreditBalance = OPDCreditBalance + %s
                WHERE EmpID = %s
            """
        db.execute_query(update_balance_query, (amount, emp_id))

        # delete the claim record
        delete_claim_query = "DELETE FROM claim WHERE ClaimID = %s"
        db.execute_query(delete_claim_query, (claim_id,))

        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/get_claim_details/<int:claim_id>', methods=['GET'])
def get_claim_details(claim_id):
    try:
        emp_id = session.get('emp_id')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching employee details'}), 500
    
    try:
        query = """
        SELECT 
            claim.Amount, 
            claim.Category, 
            claim.EmpMessage,
            claimimage.Image
        FROM 
            claim
        JOIN 
            claimimage ON claim.ClaimID = claimimage.ClaimID
        WHERE 
            claim.ClaimID = %s;
        """
        
        claim_data = db.fetch_data(query, (claim_id,))
        
        if not claim_data:
            return jsonify({'error': 'Claim not found'}), 404

        # Initialize an empty dictionary for the response
        claim_details = {
            'amount': claim_data[0][0],  # Claim Amount
            'category': claim_data[0][1],  # Claim Category
            'empMessage': claim_data[0][2],  # Employee Message
            'images': []  # List to store image URLs
        }

        # Loop through claim_data to extract all image URLs
        for row in claim_data:
            image_url = row[3]  # ClaimImage.Image is at index 3
            if image_url:  # If the image URL exists
                claim_details['images'].append(image_url)  # Add the image URL to the list

        return jsonify(claim_details)
    
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/update_claim/<int:claim_id>', methods=['POST'])
def update_claim(claim_id):
    try:
        emp_id = session.get('emp_id')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching employee details'}), 500
    
    try:
        amount = request.form.get('amount')
        emp_message = request.form.get('empMessage')
        category = request.form.get('category')

        if not amount :
            return jsonify({'error': 'Missing required fields'}), 400
        
        # fetch the claim details
        claim_query = "SELECT Amount FROM claim WHERE ClaimID = %s"
        claim = db.fetch_data(claim_query, (claim_id,))

        if not claim:
            return jsonify({'error': 'Claim not found'}), 404

        prev_amount = claim[0][0]
        
        update_balance_query = "SELECT FuelCreditBalance, OPDCreditBalance FROM credit WHERE EmpID = %s"
        credit_balances = db.fetch_data(update_balance_query, (emp_id,))
        fuel_credit_balance, opd_credit_balance = credit_balances[0]

        amount = Decimal(amount)
        prev_amount = Decimal(prev_amount)

        # update the relevant credit balance if the status is Approved
        if category == 'Fuel':
            if fuel_credit_balance + prev_amount < amount:
                return jsonify({'error': 'Insufficient fuel credit balance'}), 400
            
            fuel_credit_balance = fuel_credit_balance + prev_amount - amount

            update_balance_query = """
                UPDATE credit
                SET FuelCreditBalance = %s
                WHERE EmpID = %s
            """
            db.execute_query(update_balance_query, (fuel_credit_balance, emp_id))

        elif category == 'OPD':
            if opd_credit_balance < amount:
                return jsonify({'error': 'Insufficient OPD credit balance'}), 400
            
            opd_credit_balance = opd_credit_balance + prev_amount - amount

            update_balance_query = """
                UPDATE credit
                SET OPDCreditBalance = %s
                WHERE EmpID = %s
            """
            db.execute_query(update_balance_query, (opd_credit_balance, emp_id))

        else:
            return jsonify({'error': 'Invalid claim category'}), 400
    
        update_query = """
            UPDATE claim 
            SET DateOfRequest = %s
            WHERE ClaimID = %s;
        """
        db.execute_query(update_query, (datetime.now(), claim_id))

        # SQL query to update the claim details
        update_query = """
            UPDATE claim
            SET Amount = %s, EmpMessage = %s
            WHERE ClaimID = %s
        """
        db.execute_query(update_query, (amount, emp_message, claim_id))

        return jsonify({'success': 'Claim updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500




""" Employee Claim Request Form Function"""

@app.route('/emp_form', methods=['GET', 'POST'])
def emp_form():
    
    
    try:
        emp_name = session.get('emp_name')
        emp_id = session.get('emp_id')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching employee details'}), 500

    # fetch credit balance
    fuel_credit_balance = db.fetch_data("SELECT FuelCreditBalance FROM credit WHERE EmpID = %s", (emp_id,))
    fuel_credit_balance = fuel_credit_balance[0][0] if fuel_credit_balance else 0
    opd_credit_balance = db.fetch_data("SELECT OPDCreditBalance FROM credit WHERE EmpID = %s", (emp_id,))
    opd_credit_balance = opd_credit_balance[0][0] if opd_credit_balance else 0

    if request.method == 'POST':
        status = 'Pending'
        form_amount = request.form['amount'].strip()
        category = request.form['category'].strip()
        images = request.files.getlist('images[]')
        message = request.form['message'].strip()

        try:
            amount = Decimal(form_amount)
        except:
            amount = Decimal(0)
        
        # credit balance check
        category_field = "FuelCreditBalance" if category == 'Fuel' else "OPDCreditBalance"
        balance_query = f"SELECT {category_field} FROM credit WHERE EmpID = %s"
        balance = db.fetch_data(balance_query, (emp_id,))
        balance = balance[0][0] if balance else Decimal(0)

        if balance < amount:
            return jsonify({"error": f"Insufficient {category} credit balance. Your current balance is {balance} LKR."}), 400
        
        hash_list = []

        # process uploaded images
        if images:
            for image in images:
                if allowed_file(image.filename):

                    # pointer at the start
                    image.stream.seek(0)  
                    pil_image = Image.open(image)

                    try:
                        hash_val = get_fast_image_hash(pil_image)
                        hash_list.append(str(hash_val))
                    except Exception as e:
                        return jsonify({"error": "Internal Server Error"}), 500

                    # check if image hash exists in DB
                    query = "SELECT ClaimID FROM claimimage WHERE ImageHash = %s"
                    ex_claim_id = db.fetch_data(query, (hash_list[-1],))
                    ex_claim_id = ex_claim_id[0][0] if ex_claim_id else None

                    if ex_claim_id is not None:
                        query = """
                            SELECT DateOfRequest, Status FROM claim
                            WHERE ClaimID = %s AND Status IN ('Approved', 'Pending')
                        """
                        ex_record = db.fetch_data(query, (ex_claim_id,))
                        if ex_record and ex_record[0][1] == 'Approved':
                            date_of_request = ex_record[0][0].strftime("%d %B %Y")
                            return jsonify({"error": f"This invoice is already approved on {date_of_request}. Please contact HR if you did not submit this invoice."}), 400
                        elif ex_record and ex_record[0][1] == 'Pending':
                            return jsonify({"error": "This invoice is already marked as Pending. Please contact HR if you did not submit this invoice."}), 400

                else:
                    return jsonify({"error": "Invalid file format. Please upload only PNG, JPG, or JPEG images."}), 400
        else:
            return jsonify({"error": "No images uploaded. Please upload at least one image of the invoice."}), 400
            
        # Insert claim into the database
        query = """
            INSERT INTO claim (EmpID, Category, Amount, Status, EmpMessage, DateOfRequest)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (emp_id, category, amount, status, message, datetime.now().date()))

        # Retrieve ClaimID of the newly inserted claim
        max_claim_id = db.fetch_data("SELECT MAX(ClaimID) FROM claim")
        next_claim_id = max_claim_id[0][0] if max_claim_id and max_claim_id[0][0] is not None else 1

        # Save uploaded images
        for i, image in enumerate(images):
            if image and allowed_file(image.filename):
                image.stream.seek(0)  # Reset stream pointer before saving

                # Fetch next ImageID
                max_img_id = db.fetch_data("SELECT MAX(ImageID) FROM claimimage")
                next_img_id = max_img_id[0][0] + 1 if max_img_id and max_img_id[0][0] is not None else 1

                # Save file
                file_extension = os.path.splitext(image.filename)[1].lower()
                filename = f"{next_img_id}{file_extension}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with open(filepath, "wb") as f:
                    f.write(image.read())

                # Store the image path in the database (only hash and image path, no OCR data)
                query = "INSERT INTO claimimage (ClaimID, Image, ImageHash) VALUES (%s, %s, %s)"
                db.execute_query(query, (next_claim_id, filename, hash_list[i]))

        if category == 'Fuel':
            update_balance_query = """
                UPDATE credit
                SET FuelCreditBalance = FuelCreditBalance - %s
                WHERE EmpID = %s
            """
        elif category == 'OPD':
            update_balance_query = """
                UPDATE credit
                SET OPDCreditBalance = OPDCreditBalance - %s
                WHERE EmpID = %s
            """
        db.execute_query(update_balance_query, (form_amount, emp_id))
        
        return jsonify({"success": "Your request has been marked as pending. Thank you."}), 200

    return render_template(
        'emp_form.html',
        emp_name=emp_name,
        fuel_credit_balance=fuel_credit_balance,
        opd_credit_balance=opd_credit_balance
    )

def get_fast_image_hash(image):
    """Fast perceptual hash for duplicate detection"""
    try:
        # Use a smaller image for faster hashing
        small_image = image.resize((8, 8), Image.LANCZOS)
        return str(imagehash.phash(small_image))
    except Exception as e:
       
        return None


""" Admin Dashboard Function"""

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    admin_name = session.get('admin_name')
    today_date = date.today()

    # Retrieve selected month and year from the form
    if request.method == 'POST':
        selected_month = int(request.form.get('month', today_date.month))
        selected_year = int(request.form.get('year', today_date.year))
    else:
        # Default to current month and year for GET requests
        selected_month = int(request.args.get('month', today_date.month))
        selected_year = int(request.args.get('year', today_date.year))

    # Fetch total employees
    employee_count_query = "SELECT COUNT(*) FROM employee"
    employee_count = db.fetch_data(employee_count_query)[0][0]

    # Fetch today's claims
    today_claims_query = f"""
        SELECT SUM(c.Amount) 
        FROM claim c
        JOIN claimapproval ca ON c.ClaimID = ca.ClaimID
        WHERE c.Status = 'Approved' AND ca.DateOfApproval = '{today_date}'
"""
    today_claims = db.fetch_data(today_claims_query)[0][0] or 0

    # Fetch monthly claims
    monthly_claims_query = f"""
        SELECT SUM(Amount) 
        FROM claim 
        WHERE Status = 'Approved' 
          AND MONTH(DateOfRequest) = {selected_month} 
          AND YEAR(DateOfRequest) = {selected_year}
    """
    monthly_claims = db.fetch_data(monthly_claims_query)[0][0] or 0

    # Fetch claims breakdown (Fuel, OPD, Stationary)
    claims_breakdown_query = f"""
        SELECT 
            SUM(CASE WHEN Category = 'Fuel' THEN Amount ELSE 0 END) AS Fuel,
            SUM(CASE WHEN Category = 'OPD' THEN Amount ELSE 0 END) AS OPD,
            SUM(CASE WHEN Category = 'Stationary' THEN Amount ELSE 0 END) AS Stationary
        FROM claim 
        WHERE Status = 'Approved' 
          AND MONTH(DateOfRequest) = {selected_month} 
          AND YEAR(DateOfRequest) = {selected_year}
    """
    claims_breakdown_result = db.fetch_data(claims_breakdown_query)
    fuel_claims = claims_breakdown_result[0][0] if claims_breakdown_result else 0
    opd_claims = claims_breakdown_result[0][1] if claims_breakdown_result else 0
    stationary_claims = claims_breakdown_result[0][2] if claims_breakdown_result else 0

    # Fetch monthly trend data
    monthly_trend_query = """
        SELECT 
            MONTH(DateOfRequest) AS Month, 
            SUM(CASE WHEN Category = 'Fuel' THEN Amount ELSE 0 END) AS Fuel,
            SUM(CASE WHEN Category = 'OPD' THEN Amount ELSE 0 END) AS OPD,
            SUM(Amount) AS Total 
        FROM claim 
        WHERE Status = 'Approved' 
        GROUP BY MONTH(DateOfRequest)
    """
    monthly_trend_data = {
    'total': [0] * 12,
    'fuel': [0] * 12,
    'opd': [0] * 12
    }

    for row in db.fetch_data(monthly_trend_query):
        month_index = row[0] - 1
        monthly_trend_data['total'][month_index] = row[3]  # Total claims
        monthly_trend_data['fuel'][month_index] = row[1]  # Fuel claims
        monthly_trend_data['opd'][month_index] = row[2]   # OPD claims

    # Fetch employee claims for the selected month/year
    employee_claims_query = f"""
        SELECT 
            e.EmpID, e.FirstName, e.LastName, 
            SUM(CASE WHEN c.Category = 'Fuel' THEN c.Amount ELSE 0 END) AS Fuel,
            SUM(CASE WHEN c.Category = 'OPD' THEN c.Amount ELSE 0 END) AS OPD,
            SUM(c.Amount) AS Total
        FROM employee e
        LEFT JOIN claim c ON e.EmpID = c.EmpID
        LEFT JOIN claimapproval ca ON c.ClaimID = ca.ClaimID
        WHERE MONTH(c.DateOfRequest) = {selected_month} 
          AND YEAR(c.DateOfRequest) = {selected_year}
          AND c.Status = 'Approved'
        GROUP BY e.EmpID, e.FirstName, e.LastName
    """
    employee_claims = db.fetch_data(employee_claims_query)

    # Fetch total claims for the year
    year_claims_query = f"""
        SELECT SUM(Amount)
        FROM claim 
        WHERE Status = 'Approved' 
        AND YEAR(DateOfRequest) = {selected_year}
    """
    year_claims = db.fetch_data(year_claims_query)[0][0] or 0

    # Handle PDF download
    if 'download' in request.form:
        with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)  # Ensuring proper margins
            pdf.add_page()

            # Add logo
            logo_path = "static/img/Acorn.png"
            pdf.image(logo_path, x=10, y=8, w=30)  # Adjust size and position

            # Title with better positioning
            pdf.set_font("Arial", 'B', 20)
            pdf.cell(200, 15, txt="Claims Report", ln=True, align='C')
            pdf.ln(5)

            # Subheading with month and year
            pdf.set_font("Arial", 'I', 12)
            pdf.cell(200, 10, txt=f"Month: {selected_month}  |  Year: {selected_year}", ln=True, align='C')
            pdf.ln(10)

            # Adding a horizontal line for professionalism
            pdf.set_draw_color(0, 0, 0)  # Black color
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Draws a line across the page
            pdf.ln(5)

            # Table headers with a background color
            pdf.set_fill_color(200, 200, 200)  # Light gray background
            pdf.set_font("Arial", 'B', 12)
            headers = ["Emp ID", "Name", "Fuel (LKR)", "OPD (LKR)", "Total (LKR)"]
            col_widths = [25, 50, 40, 40, 40]

            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, txt=header, border=1, align='C', fill=True)
            pdf.ln()

            # Table rows with alternating row colors
            pdf.set_font("Arial", '', 12)
            fill = False  # Alternate row color
            total_fuel = total_opd = total_claims = 0  # Summary calculations

            for claim in employee_claims:
                emp_id = str(claim[0]) if claim[0] is not None else "N/A"
                name = f"{claim[1]} {claim[2]}" if claim[1] and claim[2] else "N/A"
                fuel = float(claim[3]) if claim[3] else 0
                opd = float(claim[4]) if claim[4] else 0
                total = float(claim[5]) if claim[5] else 0

                total_fuel += fuel
                total_opd += opd
                total_claims += total

                row = [emp_id, name, f"{fuel:.2f}", f"{opd:.2f}", f"{total:.2f}"]

                for i in range(len(headers)):
                    pdf.cell(col_widths[i], 10, txt=row[i], border=1, align='C', fill=fill)
                pdf.ln()
                fill = not fill  # Toggle fill color for alternating row effect

            # Add a summary section at the bottom
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(155, 10, txt="Total:", border=1, align='R', fill=True)
            pdf.cell(40, 10, txt=f"{total_claims:.2f} LKR", border=1, align='C', fill=True)
            pdf.ln()

            # Save PDF to temporary file
            pdf.output(temp_pdf.name)

            # Return PDF for download
            return send_file(temp_pdf.name, as_attachment=True, download_name="claims_report.pdf")

    if 'download_excel' in request.form:
        if pd is None:
            return jsonify({'error': 'Excel export not available - pandas not installed'}), 500
        
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')

        # Convert employee claims data to DataFrame
        df = pd.DataFrame(employee_claims, columns=["Emp ID", "First Name", "Last Name", "Fuel", "OPD", "Total"])
        df.to_excel(writer, sheet_name='Claims Report', index=False)

        writer.close()
        output.seek(0)

        return send_file(output, as_attachment=True, download_name="claims_report.xlsx",
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Render the page with dynamic data
    return render_template(
        'admin.html',
        employee_count=employee_count,
        today_claims=today_claims,
        monthly_claims=monthly_claims,
        fuel_claims=fuel_claims,
        opd_claims=opd_claims,
        stationary_claims=stationary_claims,
        monthly_trend_data=monthly_trend_data,
        employee_claims=employee_claims,
        selected_month=selected_month,
        selected_year=selected_year,
        admin_name=admin_name,
        year_claims=year_claims
    )


@app.route('/employee_count', methods=['GET'])
def employee_count():

    # query to count employees
    query = "SELECT COUNT(*) FROM employee"
    result = db.fetch_data(query)

    # fetch the count from the result (assuming result is a list of tuples)
    count = result[0][0] if result else 0
    return {'count': count}



""" Claim Requests Function"""
@app.route('/claim_requests', methods=['GET', 'POST'])
def claim_requests():
    
    try: 
        admin_name = session.get('admin_name')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching admin details'}), 500

    # Fetch all claims for admin review
    query_1 = """
        SELECT 
            ClaimID, EmpID, DateOfRequest, Amount, Category
        FROM 
            claim
        WHERE 
            claim.Status = 'Pending'
        ORDER BY 
            claim.ClaimID DESC;
        """
    claims = db.fetch_data(query_1)

    query_2 = """
        SELECT 
            claim.ClaimID, 
            claim.EmpID,
            employee.FirstName, 
            employee.LastName,
            employee.Email,
            employee.SBU,
            employee.TpNo,
            claim.DateOfRequest, 
            claim.Amount, 
            claim.Category, 
            claim.Status, 
            claim.EmpMessage, 
            claimimage.Image
        FROM 
            claim
        JOIN 
            employee ON claim.EmpID = employee.EmpID
        LEFT JOIN 
            claimimage ON claim.ClaimID = claimimage.ClaimID
        WHERE 
            claim.Status = 'Pending'
        ORDER BY 
            claim.ClaimID DESC;
        """
    
    # fetch the claim details from the database
    claim_details = db.fetch_data(query_2)

    # initialize an empty dictionary to store claim details
    claim_details_dict = {}

    # loop through the query result and populate the dictionary
    for claim_id, emp_id, first_name, last_name, email, sbu, tp_no, date_of_request, amount, category, status, emp_message, image_url in claim_details:
        # check if the claim_id already exists in the dictionary
        if claim_id not in claim_details_dict:
            # ceate a new entry for this claim ID, adding all claim-related info
            claim_details_dict[claim_id] = {
                'ClaimID': claim_id,
                'EmpID' : emp_id,
                'DateOfRequest': date_of_request.strftime('%d-%m-%Y') if date_of_request else None,
                'Amount': amount,
                'Category': category,
                'Status': status,
                'EmpMessage': emp_message,
                'Employee': {
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Email': email,
                    'SBU': sbu,
                    'TpNo': tp_no
                },
                'Images': []
            }
        
        # append the image URL for this claim (if exists)
        if image_url:
            claim_details_dict[claim_id]['Images'].append(image_url)

    # render the claim requests page
    return render_template(
        'claim_requests.html', 
        claims=claims, 
        admin_name=admin_name, 
        claim_details_dict=claim_details_dict
    )

@app.route('/update_status', methods=['POST'])
def update_status():

    

    # get form data
    claim_id = request.form['claim_id']
    status = request.form['status']
    admin_id = session.get('admin_id')
    admin_message = request.form.get('admin_message', '').strip()
    date_of_approval = datetime.now().date()

    # insert into ClaimApproval table
    query = f"""
        INSERT INTO claimapproval (ClaimID, AdminID, DateOfApproval, AdminMessage)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            DateOfApproval = %s,
            AdminMessage = %s
    """
    db.execute_query(query, (claim_id, admin_id, date_of_approval, admin_message, date_of_approval, admin_message))

    # fetch the claim details
    claim_query = "SELECT EmpID, Category, Amount FROM claim WHERE ClaimID = %s"
    claim = db.fetch_data(claim_query, (claim_id,))

    if not claim:
        return jsonify({'error': 'Claim not found'}), 404
    
    emp_id, category, amount = claim[0]

    # update the relevant credit balance if the status is Approved
    if status == 'Rejected':
        if category == 'Fuel':
            update_balance_query = """
                UPDATE credit
                SET FuelCreditBalance = FuelCreditBalance + %s
                WHERE EmpID = %s
            """
        elif category == 'OPD':
            update_balance_query = """
                UPDATE credit
                SET OPDCreditBalance = OPDCreditBalance + %s
                WHERE EmpID = %s
            """
        else:
            return jsonify({'error': 'Invalid claim category'}), 400

        # execute the balance update query
        rows_affected = db.execute_query(update_balance_query, (amount, emp_id))
        if rows_affected == 0:
            return jsonify({'error': 'Insufficient balance or employee not found'}), 400

    # update claim status
    update_query = "UPDATE claim SET Status = %s WHERE ClaimID = %s"
    db.execute_query(update_query, (status, claim_id))

    return jsonify({'success': 'Request status updated successfully'}), 200



""" Recent Claim Requests Function"""

@app.route('/recent_requests', methods=['GET', 'POST'])
def recent_requests():
    
    try:
        admin_name = session.get('admin_name')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching admin details'}), 500
    
    if request.method == 'POST':
        claim_id = request.form.get('claim_id')
        new_status = request.form.get('status')
        admin_message = request.form.get('admin_message', '')
        admin_id = session.get('admin_id')

         # fetch the claim details
        claim_query = "SELECT EmpID, Category, Amount, Status FROM claim WHERE ClaimID = %s"
        claim = db.fetch_data(claim_query, (claim_id,))

        if not claim:
            return jsonify({'error': 'Claim not found'}), 404

        emp_id, category, amount, prev_status = claim[0]

        update_balance_query = "SELECT FuelCreditBalance, OPDCreditBalance FROM credit WHERE EmpID = %s"
        credit_balances = db.fetch_data(update_balance_query, (emp_id,))
        fuel_credit_balance, opd_credit_balance = credit_balances[0]

        # update the relevant credit balance if the status is Approved
        if prev_status == 'Rejected' and new_status == 'Approved':
            if category == 'Fuel':
                if fuel_credit_balance < amount:
                    return jsonify({'error': 'Insufficient fuel credit balance'}), 400
                update_balance_query = """
                    UPDATE credit
                    SET FuelCreditBalance = FuelCreditBalance - %s
                    WHERE EmpID = %s
                """
            elif category == 'OPD':
                if opd_credit_balance < amount:
                    return jsonify({'error': 'Insufficient OPD credit balance'}), 400
                update_balance_query = """
                    UPDATE credit
                    SET OPDCreditBalance = OPDCreditBalance - %s
                    WHERE EmpID = %s
                """
            else:
                return jsonify({'error': 'Invalid claim category'}), 400
            
         # update the relevant credit balance if the status is Approved
        if prev_status == 'Approved' and new_status == 'Rejected':
            if category == 'Fuel':
                update_balance_query = """
                    UPDATE credit
                    SET FuelCreditBalance = FuelCreditBalance + %s
                    WHERE EmpID = %s
                """
            elif category == 'OPD':
                update_balance_query = """
                    UPDATE credit
                    SET OPDCreditBalance = OPDCreditBalance + %s
                    WHERE EmpID = %s
                """
            
        # execute the balance update query
        db.execute_query(update_balance_query, (amount, emp_id))
    
        update_query = """
            UPDATE claim 
            SET Status = %s
            WHERE ClaimID = %s;
        """
        db.execute_query(update_query, (new_status, claim_id))

        # Also update the ClaimApproval table
        update_approval_query = """
            UPDATE claimapproval 
            SET AdminID = %s, DateOfApproval = NOW(), AdminMessage = %s
            WHERE ClaimID = %s;
        """
        db.execute_query(update_approval_query, (admin_id, admin_message, claim_id))

        return jsonify({'success': 'Request status updated successfully'}), 200
        
    # fetch claims that are Approved or Rejected
    query = """
        SELECT 
        c.ClaimID,
        e.FirstName,
        e.LastName, 
        c.DateOfRequest,
        c.Category, 
        c.Amount, 
        ca.DateOfApproval,
        a.FirstName, 
        a.LastName,
        c.Status
    FROM claim AS c
    LEFT JOIN claimapproval AS ca ON c.ClaimID = ca.ClaimID
    LEFT JOIN admin AS a ON ca.AdminID = a.AdminID
    JOIN employee AS e ON c.EmpID = e.EmpID
    WHERE c.Status IN ('Approved', 'Rejected')
    ORDER BY c.ClaimID DESC;
    """
    claims = db.fetch_data(query)

    # Fetch associated claim images
    query_detailed = """
        SELECT 
            claim.ClaimID, 
            claim.EmpID,
            employee.FirstName, 
            employee.LastName,
            employee.Email,
            employee.SBU,
            employee.TpNo,
            claim.DateOfRequest, 
            claim.Amount, 
            claim.Category, 
            claim.EmpMessage,
            claimimage.Image,
            claim.Status, 
            admin.FirstName AS AdminFirstName,
            admin.LastName AS AdminLastName,
            admin.Email AS AdminEmail,
            admin.TpNo AS AdminTpNo, 
            claimapproval.DateOfApproval,
            claimapproval.AdminMessage
        FROM 
            claim
        JOIN 
            employee ON claim.EmpID = employee.EmpID
        LEFT JOIN 
            claimimage ON claim.ClaimID = claimimage.ClaimID
        LEFT JOIN 
            claimapproval ON claim.ClaimID = claimapproval.ClaimID
        JOIN
            admin ON claimapproval.AdminID = admin.AdminID
        WHERE 
            claim.Status IN ('Approved', 'Rejected')
        ORDER BY 
            claim.ClaimID DESC;

        """
    claim_details = db.fetch_data(query_detailed)

    # Initialize an empty dictionary to store claim details
    claim_details_dict = {}

    # Loop through the claim details and populate the dictionary
    for claim_id, emp_id, first_name, last_name, email, sbu, tp_no, date_of_request, amount, category, emp_message, image_url, status, admin_fname, admin_lname, admin_email, admin_tp, approval_date, admin_message in claim_details :

        if claim_id not in claim_details_dict:
            claim_details_dict[claim_id] = {
                'ClaimID': claim_id,
                'EmpID': emp_id,
                'DateOfRequest': date_of_request.strftime('%d-%m-%Y') if date_of_request else None,
                'Amount': amount,
                'Category': category,
                'Status': status,
                'EmpMessage': emp_message,
                'Employee': {
                    'FirstName': first_name,
                    'LastName': last_name,
                    'Email': email,
                    'SBU': sbu,
                    'TpNo': tp_no
                },
                'Images': [],
                'Admin': {
                    'FirstName': admin_fname,
                    'LastName': admin_lname,
                    'Email': admin_email,
                    'TpNo': admin_tp
                },
                'Approval': {
                    'DateOfApproval': approval_date.strftime('%d-%m-%Y') if approval_date else None,
                    'AdminMessage': admin_message
                }
            }

        if image_url:
            claim_details_dict[claim_id]['Images'].append(image_url)

    # Render the template with the claims and claim details (images)
    return render_template(
        'recent_requests.html', 
        claims=claims, 
        admin_name=admin_name, 
        claim_details_dict=claim_details_dict
    )



""" Admin Create Employee Function"""

@app.route('/admin_form', methods=['GET', 'POST'])
def admin_form():

    
    try: 
        admin_name = session.get('admin_name')
    except Exception as e:
        return jsonify({'error': 'An error occurred while fetching admin details'}), 500

    if request.method == 'POST':

        # get form data
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.hash(password)
        

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        nic = request.form['nic']
        dob = request.form['dob']
        gender = request.form['gender']
        sbu = request.form['sbu']
        telephone = request.form['telephone']
        opd_credit_limit = request.form['opd_credit_limit']
        fuel_credit_limit = request.form['fuel_credit_limit']

        # insert the new employee data into the Employee table
        query = """
            INSERT INTO employee (Email, Password, FirstName, LastName, NIC, DOB, Gender, SBU, TpNo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (email, hashed_password, first_name, last_name, nic, dob, gender, sbu, telephone))

        max_emp_query = "SELECT MAX(EmpID) FROM employee"
        max_emp_id = db.fetch_data(max_emp_query)[0][0]

        # insert the new employee data into the Credit table
        credit_limit_query = """
            INSERT INTO credit (EmpID, FuelCreditLimit, OPDCreditLimit, FuelCreditBalance, OPDCreditBalance)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.execute_query(credit_limit_query, (max_emp_id, fuel_credit_limit, opd_credit_limit, 0, 0))

        # redirect to the admin dashboard after account creation
        return redirect(url_for('dashboard'))

    # render the form on GET request
    return render_template('admin_form.html', admin_name=admin_name)



""" Update Emplyee Credit Limits Function"""

@app.route('/emp_details', methods=['GET', 'POST'])
def emp_details():

    
    admin_name = session.get('admin_name')

    if request.method == 'GET':

        # execute a raw SQL query to retrieve data from Employee and Credit tables
        query = """
            SELECT e.EmpId, e.Email, e.SBU, c.FuelCreditLimit, c.OPDCreditLimit, c.FuelCreditBalance, c.OPDCreditBalance
            FROM employee e
            JOIN credit c ON e.EmpID = c.EmpID
        """
        employees = db.fetch_data(query)
        return render_template('emp_details.html', employees=employees, admin_name=admin_name)

    if request.method == 'POST':

        # handle the form submission for editing credit limits
        emp_id = request.form['emp_id']
        fuel_limit = request.form['fuel_limit']
        opd_limit = request.form['opd_limit']
        fuel_balance = request.form['fuel_balance']
        opd_balance = request.form['opd_balance']

        # update the Fuel and OPD Credit Limits for the selected employee
        query = f"""
            UPDATE credit
            SET FuelCreditLimit = %s, OPDCreditLimit = %s, FuelCreditBalance = %s, OPDCreditBalance = %s
            WHERE EmpID = %s
        """
        db.execute_query(query, (fuel_limit, opd_limit, fuel_balance, opd_balance, emp_id))
        return redirect(url_for('emp_details'))



""" Employee Update Function"""
@app.route('/emp_update', methods=['GET', 'POST'])
def emp_update():
    
    admin_name = session.get('admin_name')

    if request.method == 'GET':
        # Fetch all employees from the database
        query = "SELECT EmpID, FirstName, LastName, Email, Password, NIC, DOB, Gender, SBU, TpNo FROM employee"
        employees = db.fetch_data(query)
        return render_template('emp_update.html', employees=employees, admin_name=admin_name)

    if request.method == 'POST':
        # Get the form action (update or delete)
        action = request.form.get('action')

        if action == 'update':
            # Get the updated employee details
            emp_id = request.form['emp_id']  # Get EmpID from the form
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            password = request.form['password']
            nic = request.form['nic']
            dob = request.form['dob']
            gender = request.form['gender']
            sbu = request.form['sbu']
            tp_no = request.form['tp_no']

            # Corrected SQL query (no unnecessary quotes)
            query = """
                UPDATE employee 
                SET FirstName = %s, LastName = %s, Email = %s, Password = %s, 
                    NIC = %s, DOB = %s, Gender = %s, SBU = %s, TpNo = %s
                WHERE EmpID = %s
            """
            db.execute_query(query, (first_name, last_name, email, password, nic, dob, gender, sbu, tp_no, emp_id))
            return redirect(url_for('emp_update'))

        elif action == 'delete':
            # Get the employee ID to delete
            emp_id = request.form['emp_id']

            # Delete the employee from the database using parameterized query
            query = "DELETE FROM employee WHERE EmpID = %s"
            db.execute_query(query, (emp_id,))
            return redirect(url_for('emp_update'))



@app.route('/generate_report', methods=['GET', 'POST'])
def generate_report():
    
    admin_name = session.get('admin_name')

    employee = db.fetch_data("SELECT EmpID, FirstName, LastName FROM employee")  # Fetch employees

    if request.method == 'POST':
        # Get form data
        report_type = request.form.get('report_type')
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Prioritize employee_id_input over dropdown selection
        employee_id = None
        if report_type == 'individual':
            # First check if employee_id_input (text field) has a value
            employee_id_input = request.form.get('employee_id_input', '').strip()
            if employee_id_input:
                employee_id = employee_id_input
            else:
                # Fallback to dropdown selection if text input is empty
                employee_id = request.form.get('employee_id')
        
        

        # Construct SQL queries dynamically
        query_conditions = "WHERE Status = 'Approved' AND DateOfRequest BETWEEN %s AND %s"
        params = [start_date, end_date]

        # Get employee details for individual reports
        employee_name = None
        employee_display_id = None
        if employee_id:
            # Validate that employee_id is numeric and exists
            try:
                employee_id = int(employee_id)
                query_conditions += " AND EmpID = %s"
                params.append(employee_id)
                
                # Fetch employee details
                emp_query = "SELECT EmpID, FirstName, LastName FROM employee WHERE EmpID = %s"
                emp_result = db.fetch_data(emp_query, [employee_id])
                if emp_result:
                    employee_display_id = emp_result[0][0]
                    employee_name = f"{emp_result[0][1]} {emp_result[0][2]}"
                else:
                    # Employee ID not found, set error message or handle appropriately
                    
                    employee_name = f"Employee ID {employee_id} (Not Found)"
                    employee_display_id = employee_id
            except (ValueError, TypeError):
                # Invalid employee ID format
                
                employee_name = f"Invalid Employee ID: {employee_id}"
                employee_display_id = employee_id
                # Don't add to query conditions if invalid

        # Fetch Fuel claims
        fuel_claims_query = f"SELECT SUM(Amount) FROM claim {query_conditions} AND Category = 'Fuel'"
        fuel_claims = db.fetch_data(fuel_claims_query, params)
        fuel_total = fuel_claims[0][0] if fuel_claims and fuel_claims[0][0] is not None else 0

        # Fetch OPD claims
        opd_claims_query = f"SELECT SUM(Amount) FROM claim {query_conditions} AND Category = 'OPD'"
        opd_claims = db.fetch_data(opd_claims_query, params)
        opd_total = opd_claims[0][0] if opd_claims and opd_claims[0][0] is not None else 0

        total_claims = (fuel_total or 0) + (opd_total or 0)

        # Get current date for display
        current_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')

        return render_template(
            'report.html',
            fuel_total=fuel_total,
            opd_total=opd_total,
            total_claims=total_claims,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type,
            employee_id=employee_id,
            employee_name=employee_name,
            employee_display_id=employee_display_id,
            employees=employee,
            current_date=current_date
        )

    return render_template('generate_report.html', admin_name=admin_name, employees=employee)


@app.route('/get_employees', methods=['GET'])
def get_employees():
    employees = db.fetch_data("SELECT EmpID, FirstName, LastName FROM employee")
    employee_list = [{"id": emp[0], "name": f"{emp[1]} {emp[2]}"} for emp in employees]
    return jsonify(employee_list)


@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')

    query_conditions = "WHERE Status = 'Approved' AND DateOfRequest BETWEEN %s AND %s"
    params = [start_date, end_date]

    # Fetch employee name and ID for individual reports
    employee_name = "All Employees"
    employee_display_id = "All"
    if employee_id:
        query_conditions += " AND EmpID = %s"
        params.append(employee_id)
        
        emp_query = "SELECT EmpID, FirstName, LastName FROM employee WHERE EmpID = %s"
        emp_result = db.fetch_data(emp_query, [employee_id])
        if emp_result:
            employee_display_id = emp_result[0][0]
            employee_name = f"{emp_result[0][1]} {emp_result[0][2]}"

    # Fetch Fuel claims
    fuel_claims_query = f"SELECT SUM(Amount) FROM claim {query_conditions} AND Category = 'Fuel'"
    fuel_claims = db.fetch_data(fuel_claims_query, params)
    fuel_total = fuel_claims[0][0] if fuel_claims and fuel_claims[0][0] is not None else 0

    # Fetch OPD claims
    opd_claims_query = f"SELECT SUM(Amount) FROM claim {query_conditions} AND Category = 'OPD'"
    opd_claims = db.fetch_data(opd_claims_query, params)
    opd_total = opd_claims[0][0] if opd_claims and opd_claims[0][0] is not None else 0

    total_claims = fuel_total + opd_total

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Add logo
    logo_path = "static/img/Acorn.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=8, w=25)

    # Title
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 20, "ACORN HR - CLAIM REPORT", ln=True, align="C")
    pdf.ln(5)

    # Report type and period
    pdf.set_font("Arial", "B", 12)
    report_type = "Individual Employee Report" if employee_id else "Overall Company Report"
    pdf.cell(0, 8, f"Report Type: {report_type}", ln=True, align="C")
    pdf.cell(0, 8, f"Period: {start_date} to {end_date}", ln=True, align="C")
    pdf.ln(5)

    # Employee details for individual reports
    if employee_id:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"Employee ID: {employee_display_id}", ln=True, align="C")
        pdf.cell(0, 8, f"Employee Name: {employee_name}", ln=True, align="C")
        pdf.ln(5)

    # Line separator
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    # Claims table
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    
    # Table headers
    pdf.cell(120, 10, "Category", border=1, align="C", fill=True)
    pdf.cell(60, 10, "Amount (LKR)", border=1, align="C", fill=True)
    pdf.ln()

    # Table data
    pdf.set_font("Arial", "", 12)
    pdf.cell(120, 10, "Fuel Claims", border=1, align="L")
    pdf.cell(60, 10, f"{fuel_total:,.2f}", border=1, align="R")
    pdf.ln()
    
    pdf.cell(120, 10, "OPD Claims", border=1, align="L")
    pdf.cell(60, 10, f"{opd_total:,.2f}", border=1, align="R")
    pdf.ln()

    # Total row
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(120, 12, "TOTAL CLAIMS", border=1, align="C", fill=True)
    pdf.cell(60, 12, f"{total_claims:,.2f}", border=1, align="R", fill=True)
    pdf.ln(20)

    # Footer
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 8, f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", ln=True, align="C")

    # Generate filename
    filename = f"claim_report_{employee_name.replace(' ', '_')}_{start_date}_to_{end_date}.pdf" if employee_id else f"claim_report_overall_{start_date}_to_{end_date}.pdf"

    # Create a temporary file for the PDF
    with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
        pdf.output(temp_pdf.name)
        
        # Return the PDF file for download
        return send_file(
            temp_pdf.name, 
            as_attachment=True, 
            download_name=filename,
            mimetype='application/pdf'
        )


@app.route('/download_excel', methods=['GET'])
def download_excel():
    if pd is None:
        return jsonify({'error': 'Excel export not available - pandas not installed'}), 500
        
    # Get parameters from the request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    
    # Construct SQL queries dynamically
    query_conditions = "WHERE Status = 'Approved' AND DateOfRequest BETWEEN %s AND %s"
    params = [start_date, end_date]
    
    # Get employee details for individual reports
    employee_name = "All Employees"
    employee_display_id = "All"
    if employee_id:
        query_conditions += " AND EmpID = %s"
        params.append(employee_id)
        
        # Fetch employee details
        emp_query = "SELECT EmpID, FirstName, LastName FROM employee WHERE EmpID = %s"
        emp_result = db.fetch_data(emp_query, [employee_id])
        if emp_result:
            employee_display_id = emp_result[0][0]
            employee_name = f"{emp_result[0][1]} {emp_result[0][2]}"

    # Query for Fuel claims
    fuel_claims_query = f"SELECT SUM(Amount) FROM claim {query_conditions} AND Category = 'Fuel'"
    fuel_claims = db.fetch_data(fuel_claims_query, params)
    fuel_total = fuel_claims[0][0] if fuel_claims and fuel_claims[0][0] is not None else 0

    # Query for OPD claims
    opd_claims_query = f"SELECT SUM(Amount) FROM claim {query_conditions} AND Category = 'OPD'"
    opd_claims = db.fetch_data(opd_claims_query, params)
    opd_total = opd_claims[0][0] if opd_claims and opd_claims[0][0] is not None else 0

    # Calculate total claims
    total_claims = (fuel_total or 0) + (opd_total or 0)

    # Create DataFrame with enhanced information
    data = {
        "Report Type": ["Individual Employee Report" if employee_id else "Overall Company Report", "", ""],
        "Employee ID": [employee_display_id, "", ""],
        "Employee Name": [employee_name, "", ""],
        "Period": [f"{start_date} to {end_date}", "", ""],
        "Category": ["Fuel Claims", "OPD Claims", "Total Claims"],
        "Amount (LKR)": [fuel_total, opd_total, total_claims]
    }
    df = pd.DataFrame(data)

    # Create Excel file in memory using BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Claim Report', index=False)
    
    output.seek(0)
    
    # Generate filename based on report type
    filename = f"claim_report_{employee_name.replace(' ', '_')}_{start_date}_to_{end_date}.xlsx" if employee_id else f"claim_report_overall_{start_date}_to_{end_date}.xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/stationary', methods=['GET', 'POST'])
def stationary():
    
    today_date = date.today()
    admin_name = session.get('admin_name')

    # fetch today's claims from the database
    today_claims_query = f"""
            SELECT SUM(c.Amount) AS TotalApprovedAmount
            FROM claim c
            INNER JOIN claimapproval ca ON c.ClaimID = ca.ClaimID
            WHERE c.Status = 'Approved' 
            AND ca.DateOfApproval = '{today_date}'
        """
    today_claims = db.fetch_data(today_claims_query)

    # handle cases where there are no claims
    today_claims_total = today_claims[0][0] if today_claims and today_claims[0][0] is not None else 0

    current_month = today_date.month
    current_year = today_date.year

    # calculate the total claims for the current month
    monthly_claims_query = f"""
            SELECT SUM(Amount) 
            FROM claim 
            WHERE Status = 'Approved' 
              AND EXTRACT(MONTH FROM DateOfRequest) = %s 
              AND EXTRACT(YEAR FROM DateOfRequest) = %s
        """
    monthly_claims_result = db.fetch_data(monthly_claims_query, (current_month, current_year))

    # extract the value or set to 0 if no claims found
    monthly_claims = monthly_claims_result[0][0] if monthly_claims_result and monthly_claims_result[0][0] else 0

    # calculate monthly stationary claims
    monthly_stationary_claims_query = f"""
                SELECT SUM(Amount) 
                FROM claim 
                WHERE Status = 'Approved' 
                  AND Category = 'Stationary' 
                  AND EXTRACT(MONTH FROM DateOfRequest) = %s 
                  AND EXTRACT(YEAR FROM DateOfRequest) = %s
            """
    monthly_stationary_claims_result = db.fetch_data(monthly_stationary_claims_query, (current_month, current_year))
    monthly_stationary_claims = monthly_stationary_claims_result[0][0] if monthly_stationary_claims_result and \
                                                                          monthly_stationary_claims_result[0][0] else 0

    # handle month/year selection form
    if request.method == 'POST':
        selected_month = request.form.get('month')
        selected_year = request.form.get('year')

        # fetch claims for the selected month and year
        employee_claims_query = f"""
                    SELECT e.EmpID, e.FirstName, e.LastName, 
                           SUM(CASE WHEN c.Category = 'Stationary' THEN c.Amount ELSE 0 END) AS TotalStationary,
                           MAX(c.DateOfRequest) AS DateOfRequest, 
                           MAX(ca.DateOfApproval) AS DateOfApproval, 
                           MAX(ca.AdminID) AS ApprovedAdmin
                    FROM employee e
                    LEFT JOIN claim c ON e.EmpID = c.EmpID
                    LEFT JOIN claimapproval ca ON c.ClaimID = ca.ClaimID
                    WHERE EXTRACT(MONTH FROM c.DateOfRequest) = %s 
                      AND EXTRACT(YEAR FROM c.DateOfRequest) = %s
                      AND c.Status = 'Approved'
                    GROUP BY e.EmpID, e.FirstName, e.LastName
                    ORDER BY e.EmpID;
                """

        # fetch employee claims data for the selected month/year
        employee_claims = db.fetch_data(employee_claims_query, (selected_month, selected_year))
        # Handle download action
        return render_template(
            'stationary_admin.html',
            today_claims=today_claims_total,
            monthly_claims=monthly_claims,
            monthly_stationary_claims=monthly_stationary_claims,
            employee_claims=employee_claims,
            selected_month=selected_month,
            selected_year=selected_year,
            admin_name=admin_name
        )

    return render_template(
        'stationary_admin.html',
        today_claims=today_claims_total,
        monthly_claims=monthly_claims,
        monthly_stationary_claims=monthly_stationary_claims,
        selected_month=current_month,
        selected_year=current_year,
        admin_name=admin_name,
    )


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") != "production"
    app.run(host='0.0.0.0', port=port, debug=debug)