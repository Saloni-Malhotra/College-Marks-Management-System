from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from database import init_db, mysql
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

app = Flask(__name__)
init_db(app)

app.secret_key = 'anyrandompassword'

@app.route('/')
def index():
    return render_template('index.html')  # Renders homepage

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        # Handle POST request
        data = request.get_json()
        username = data['username']
        password = data['password']

        # Check the student table first
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM student WHERE Stud_User = %s", (username,))
        student = cur.fetchone()  # Fetch the student data

        if student:
            stored_password = student[]  # Put attribute number in []
            if password == stored_password:
                session['username'] = username  # Store username in session
                return jsonify({"success": True, "role": "student"})
            else:
                return jsonify({"success": False, "message": "Incorrect password"}), 401

        # Check the mentor table second
        cur.execute("SELECT * FROM mentor WHERE F_User = %s", (username,))
        mentor = cur.fetchone()  # Get the mentor data

        if mentor:
            stored_password = mentor[]  # Put attribute number in []
            if password == stored_password:
                session['username'] = username  # Store username in session
                return jsonify({"success": True, "role": "mentor"})
            else:
                return jsonify({"success": False, "message": "Incorrect password"}), 401

        # If the user doesn't exist
        return jsonify({"success": False, "message": "User not found"}), 404

    else:
        # Handle GET request by rendering login page
        return render_template('login.html')  #renders login page

@app.route('/mentor-dashboard')
def mentor_dashboard():
    return render_template('mentor-dashboard.html')

@app.route('/get-mentor-data')
def get_mentor_data():
    # Retrieve the username from session after login
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    cur = mysql.connection.cursor()

    # Query to fetch Name, Faculty_ID, and other necessary information
    cur.execute("SELECT Name, Faculty_ID, F_User FROM mentor WHERE F_User = %s", (username,))
    mentor = cur.fetchone()
    cur.close()

    # Return the mentor data in JSON format
    if mentor:
        return jsonify({"name": mentor[0], "faculty_id": mentor[1]})
    else:
        return jsonify({"error": "Mentor not found"}), 404

@app.route('/my-mentees')
def my_mentees():
    # Retrieve the username from session after login
    username = session.get('username')

    if not username:
        return jsonify({'error': 'Not logged in'}), 401

    cur = mysql.connection.cursor()

    # Query to fetch the Mentee_USN for the logged-in mentor
    cur.execute("SELECT Mentee_USN FROM mentor WHERE F_User = %s", (username,))
    mentor = cur.fetchone()
    cur.close()

    if mentor:
        # Mentee_USN is stored as a space-separated string
        mentees_usn = mentor[0]
        mentees_list = mentees_usn.split()  # Split the string into a list of USNs

        # Fetch student details (name and phone) for each USN
        mentees_info = []
        cur = mysql.connection.cursor()
        for usn in mentees_list:
            cur.execute("SELECT Stud_Name, Stud_PhNo FROM student WHERE USN = %s", (usn,))
            student = cur.fetchone()
            if student:
                mentees_info.append({
                    "usn": usn,
                    "name": student[0],
                    "phone": student[1]
                })
        cur.close()

        return render_template('my_mentees.html', mentees=mentees_info)
    else:
        return jsonify({"error": "Mentor not found"}), 404

@app.route('/enter-mentee-marks', methods=['GET', 'POST'])
def enter_mentee_marks():
    # Ensure mentor is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Handle form submission
    if request.method == 'POST':
        semester = request.form['semester']

        # If USN not in form, this is the semester-selection step
        if 'USN' not in request.form:
            cur = mysql.connection.cursor()
            cur.execute("SELECT Mentee_USN FROM mentor WHERE F_User = %s", (session['username'],))
            raw = cur.fetchone()[0]
            cur.close()
            mentees_usn = raw.split()

            # Fetch subjects for the chosen semester
            cur = mysql.connection.cursor()
            cur.execute(f"SELECT Sem{semester} FROM subjects WHERE Dept_Name='CSE'")
            row = cur.fetchone()
            cur.close()
            if not row or not row[0]:
                flash("No subjects found for semester " + semester, "danger")
                return redirect(url_for('enter_mentee_marks'))

            subjects_list = row[0].split()  # e.g. ["BCS301","BCS302", ...]

            # Render form
            return render_template(
                'enter-mentee-marks.html',
                step='marks',
                semester=semester,
                mentees_usn=mentees_usn,
                subjects=subjects_list
            )

        mentee_usn = request.form['USN']
        semester = request.form['semester']
        cur = mysql.connection.cursor()
        cur.execute(f"SELECT Sem{semester} FROM subjects WHERE Dept_Name='CSE'")
        row = cur.fetchone()
        cur.close()
        subjects_list = row[0].split()
        marks = { subj: request.form.get(f"subject_{subj}") for subj in subjects_list }
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1 FROM marks WHERE USN=%s", (mentee_usn,))
        exists = cur.fetchone() is not None

        if not exists:
            cur.execute("INSERT INTO marks (USN) VALUES (%s)", (mentee_usn,))

        for subj, mark in marks.items():
            cur.execute(f"UPDATE marks SET `{subj}` = %s WHERE USN = %s", (mark, mentee_usn))

        mysql.connection.commit()
        cur.close()

        flash(f"Marks for {mentee_usn} (Sem {semester}) saved.", "success")
        return redirect(url_for('enter_mentee_marks'))


    return render_template('enter-mentee-marks.html', step='semester')


@app.route('/student-dashboard')
def student_dashboard():
    return render_template('student-dashboard.html')

@app.route('/get-student-data')
def get_student_data():

    student_user = session.get('username')
    if not student_user:
        return jsonify({'error': 'Not logged in'}), 401

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT Stud_Name, USN FROM student WHERE Stud_User = %s",
        (student_user,)
    )
    student = cur.fetchone()
    cur.close()

    if student:
        return jsonify({"name": student[0], "usn": student[1]})
    else:
        return jsonify({'error': 'Student not found'}), 404


@app.route('/view-marksheet', methods=['GET','POST'])
def view_marksheet():
    if 'username' not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        semester = int(request.form['semester'])
        stud_user = session['username']

        # Lookup real USN
        cur = mysql.connection.cursor()
        cur.execute("SELECT USN, Stud_Name FROM student WHERE Stud_User = %s",
                    (stud_user,))
        student_row = cur.fetchone()
        cur.close()
        if not student_row:
            flash("Your student record wasn’t found.", "danger")
            return redirect(url_for('view_marksheet'))
        usn, student_name = student_row

        #Fetch subjects
        cur = mysql.connection.cursor()
        cur.execute(f"SELECT Sem{semester} FROM subjects WHERE Dept_Name='CSE'")
        row = cur.fetchone()
        if not row or not row[0]:
            flash("No subjects defined for this semester.", "danger")
            return redirect(url_for('view_marksheet'))
        subjects = row[0].split()

        #Fetch marks
        cols = ", ".join(f"`{s}`" for s in subjects)
        cur.execute(f"SELECT {cols} FROM marks WHERE USN=%s", (usn,))
        marks_row = cur.fetchone()
        cur.close()
        if marks_row is None:
            flash("No marks entered yet for this semester.", "danger")
            return redirect(url_for('view_marksheet'))

        # Fetch credits
        cur = mysql.connection.cursor()
        cur.execute("SELECT cred4,cred3,cred2,cred1,cred0 FROM credits WHERE Dept_Name='CSE'")
        cred_row = cur.fetchone()
        cur.close()
        if not cred_row:
            flash("Credit data missing.", "danger")
            return redirect(url_for('view_marksheet'))

        credit_map = {}
        for cv, slist in zip([4,3,2,1,0], cred_row):
            for subj_code in slist.split():
                credit_map[subj_code.strip().upper()] = cv

        # Build table_data & compute SGPA
        total_credits = weighted_points = 0
        table_data = []
        for subj, raw in zip(subjects, marks_row):
            m = raw if raw is not None else 0
            cr = credit_map.get(subj.upper(), 0)
            # VTU 2022 GP Calc
            if m >= 90: gp = 10
            elif m >= 80: gp = 9
            elif m >= 70: gp = 8
            elif m >= 60: gp = 7
            elif m >= 50: gp = 6
            elif m >= 45: gp = 5
            elif m >= 40: gp = 4
            else: gp = 0

            total_credits   += cr
            weighted_points += cr * gp
            table_data.append((subj, m, cr, gp))

        sgpa = round(weighted_points/total_credits, 2) if total_credits else 0

        # Generate PDF via Platypus
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                title=f"{usn}_Sem{semester}_Marksheet")
        styles = getSampleStyleSheet()

        elems = []
        # Logo + Title
        elems.append(Image("static/collegelogo.png", width=130, height=80))
        elems.append(Paragraph(
            "<br/><b>Insert College Name</b><br/>"
            "<br/>"
            "<br/>"
            f"<i>Marksheet — Semester {semester}</i><br/>"
            "<br/>"
            "<br/>",
            ParagraphStyle('Title', fontSize=18, alignment=1)
        ))
        elems.append(Spacer(1, 12))

        # Student Info
        info = [
            ["Student Name:", student_name],
            ["USN:", usn],
            ["SGPA:", str(sgpa)]
        ]
        tbl = Table(info, colWidths=[120, 200])
        tbl.setStyle(TableStyle([
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
            ('TEXTCOLOR',    (0,0), (0,-1),   colors.darkblue),
            ('BOTTOMPADDING',(0,0), (-1,-1),  6),
        ]))
        elems.extend([tbl, Spacer(1, 20)])

        # Marks Table
        data = [["Subject","Marks","Credits","GPA"]] + [
            [subj, str(m), str(cr), str(gp)]
            for subj, m, cr, gp in table_data
        ]
        marks_tbl = Table(data, colWidths=[120,60,60,60])
        marks_tbl.setStyle(TableStyle([
            ('BACKGROUND',     (0,0), (-1,0),    colors.HexColor('#2563EB')),
            ('TEXTCOLOR',      (0,0), (-1,0),    colors.white),
            ('ALIGN',          (1,1), (-1,-1),   'CENTER'),
            ('GRID',           (0,0), (-1,-1),   0.5, colors.grey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),   [colors.whitesmoke, colors.lightgrey]),
            ('FONTNAME',       (0,0), (-1,0),    'Helvetica-Bold'),
        ]))
        elems.append(marks_tbl)

        # Faculty Sign
        elems.append(Spacer(1, 40))
        elems.append(Paragraph("<br/><br/><br/>__________________________", styles['Normal']))
        elems.append(Paragraph("<i>  Mentor/HoD Signature</i>  ", styles['Normal']))

        doc.build(elems)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{usn}_Sem{semester}_Marksheet.pdf",
            mimetype='application/pdf'
        )

    return render_template('select-semester.html')

if __name__ == '__main__':
    app.run(debug=True)
