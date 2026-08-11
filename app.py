from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prisma import Prisma
import urllib.parse
import os

app = Flask(__name__)
app.secret_key = "super_secret_sih_key_phase_2"

# FIREWALL: Rate Limiting to prevent spam & DDoS attacks
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

db = Prisma()
db.connect()

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/explore')
def explore():
    campus_filter = request.args.get('campus', 'All')
    search_query = request.args.get('q', '').lower()
    
    query_args = {"include": {"leader": True}, "order": {"created_at": "desc"}}
    if campus_filter in ['JIIT 128', 'JIIT 62']:
        query_args["where"] = {"campus": campus_filter}
        
    teams = db.team.find_many(**query_args)
    
    if search_query:
        teams = [t for t in teams if search_query in t.team_name.lower() or search_query in t.required_skills.lower()]

    # Pass the current logged-in user ID to the template to show/hide the Delete button
    user_id = session.get('user_id')
    return render_template('index.html', teams=teams, current_campus=campus_filter, current_user_id=user_id)

# --- AUTHENTICATION ROUTES ---

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # Strict firewall on auth routes
def signup():
    if request.method == 'POST':
        email = request.form['email'].lower()
        # Check if email exists
        existing_user = db.user.find_unique(where={"email": email})
        if existing_user:
            flash("Email already registered. Please log in.")
            return redirect(url_for('login'))
            
        hashed_pw = generate_password_hash(request.form['password'])
        
        user = db.user.create(
            data={
                "name": request.form['name'],
                "email": email,
                "password_hash": hashed_pw,
                "whatsapp_number": request.form['whatsapp_number'],
                "campus": request.form['campus']
            }
        )
        session['user_id'] = user.id
        session['user_name'] = user.name
        flash("Account created successfully!")
        return redirect(url_for('explore'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute") # Brute-force protection
def login():
    if request.method == 'POST':
        user = db.user.find_unique(where={"email": request.form['email'].lower()})
        
        if user and check_password_hash(user.password_hash, request.form['password']):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash(f"Welcome back, {user.name}!")
            return redirect(url_for('explore'))
        else:
            flash("Invalid email or password.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('landing'))

# --- TEAM MANAGEMENT ---

@app.route('/create', methods=['GET', 'POST'])
def create_team():
    # Protect route: Only logged-in users can create teams
    if 'user_id' not in session:
        flash("You must be logged in to create a team.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        db.team.create(
            data={
                "leader_id": session['user_id'],
                "team_name": request.form['team_name'],
                "campus": request.form['campus'],
                "current_members": int(request.form['current_members']),
                "max_members": 6,
                "required_skills": request.form['required_skills'],
                "description": request.form.get('description', '')
            }
        )
        flash("TEAM LISTING PUBLISHED SUCCESSFULLY!")
        return redirect(url_for('explore'))
        
    return render_template('create.html')

@app.route('/delete/<team_id>', methods=['POST'])
def delete_team(team_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    team = db.team.find_unique(where={"id": team_id})
    
    # SECURITY: Ensure the person deleting the team is the actual leader
    if team and team.leader_id == session['user_id']:
        db.team.delete(where={"id": team_id})
        flash("Team listing deleted successfully.")
    else:
        flash("Unauthorized action.")
        
    return redirect(url_for('explore'))

@app.route('/contact/<team_id>')
@limiter.limit("20 per hour") # Prevent bot scraping of WhatsApp links
def contact_team(team_id):
    team = db.team.find_unique(where={'id': team_id}, include={'leader': True})
    if not team:
        return "Team not found", 404
        
    phone = team.leader.whatsapp_number
    phone = ''.join(filter(str.isdigit, phone))
    msg = f"Hi {team.leader.name}, I found '{team.team_name}' on SIH Team Builder! I'm interested in joining. Are you still looking for members?"
    encoded_msg = urllib.parse.quote(msg)
    
    return redirect(f"https://wa.me/{phone}?text={encoded_msg}")
@app.route('/talent')
def explore_talent():
    # Fetch all talent profiles, including the user's name from the linked User table
    talents = db.talentprofile.find_many(
        include={
            'user': True
        },
        order={
            'createdAt': 'desc'
        }
    )
    return render_template('talent.html', talents=talents)

@app.route('/talent/join', methods=['GET', 'POST'])
def join_talent_pool():
    if 'user_id' not in session:
        flash('You must be logged in to join the talent pool.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Check if user already has a profile to prevent duplicates
    existing_profile = db.talentprofile.find_first(where={'userId': user_id})

    if request.method == 'POST':
        skills = request.form.get('skills')
        bio = request.form.get('bio')
        whatsapp = request.form.get('whatsapp')
        campus = request.form.get('campus')

        if existing_profile:
            # Update existing
            db.talentprofile.update(
                where={'id': existing_profile.id},
                data={
                    'skills': skills,
                    'bio': bio,
                    'whatsapp': whatsapp,
                    'campus': campus
                }
            )
            flash('Talent profile updated successfully!', 'success')
        else:
            # Create new
            db.talentprofile.create(
                data={
                    'userId': user_id,
                    'skills': skills,
                    'bio': bio,
                    'whatsapp': whatsapp,
                    'campus': campus
                }
            )
            flash('You are now in the talent pool!', 'success')
            
        return redirect(url_for('explore_talent'))

    return render_template('join_talent.html', existing_profile=existing_profile)

if __name__ == '__main__':
    app.run(debug=True)