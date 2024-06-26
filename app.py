from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify
from db import db
from collections import defaultdict

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        ref = db.reference("staff_details")
        data = ref.get()
        staff_names = [details['name'] for uid, details in data.items() if details.get('department') == 'PR']
        return render_template('home.html', staff_names=staff_names)
    else:
        pass

@app.route('/assign', methods=['POST'])
def assign():
    staff_name = request.form.get('staffName')
    team = request.form.get('team')
    role = request.form.get('role')
    
    today = datetime.now()
    start_of_week  =  today - timedelta(days=today.weekday())
    weekly_timestamp = start_of_week.strftime('%Y-%m-%d')
    
    if role == "pr" or role == "manager":
        weekly_target = {
            "points": "200",
            "sales": "20",
            "visits": "40"
        }  
    elif role == "tc":
        weekly_target = {
            "visits": "40"
        }
    else:
        return "Invalid Role"
        
    db_path = f"sales_performance/{team}/{role}/{staff_name}/{weekly_timestamp}/weekly_target"
    ref = db.reference(db_path)
    ref.set(weekly_target)

    return redirect(url_for('home'))

@app.route('/update_weekly_tar', methods=['POST'])
def update_weekly_target():
    staff_name = request.form.get('staffName_')
    team = request.form.get('team')
    role = request.form.get('role')
    points = request.form.get('points')
    sales = request.form.get('sales')
    visits = request.form.get('visits')
    week = request.form.get('week')
    
    year, week_number = map(int, week.split('-W'))
    week_date = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()

    if role == "pr" or role == "manager":
        weekly_target = {
            "points": points,
            "sales": sales,
            "visits": visits
        }  
    elif role == "tc":
        weekly_target = {
            "visits": visits
        }
    else:
        return "Invalid Role"

    db_path = f"sales_performance/{team}/{role}/{staff_name}/{week_date}/weekly_target"
    ref = db.reference(db_path)
    ref.set(weekly_target)
    return redirect(url_for('home'))

@app.route('/get_names', methods=['POST'])
def get_names():
    team = request.form.get('team')
    role = request.form.get('role')
    
    ref = db.reference(f"sales_performance/{team}/{role}")
    data = ref.get() or {}

    staff_names = list(data.keys())  
    return jsonify(staff_names)

@app.route('/get_deaily_perfomence', methods=['POST'])
def get_deaily_perfomence():
    team = request.form.get('team')
    role = request.form.get('role')
    name = request.form.get('staffName')
    date = request.form.get('date')
    
    date = datetime.strptime(date, '%Y-%m-%d')
    first_day_of_week = date - timedelta(days=date.weekday())
    first_date_of_week = first_day_of_week.strftime('%Y-%m-%d')
    
    ref = db.reference(f"sales_performance/{team}/{role}/{name}/{first_date_of_week}")
    data = ref.get() or {}

    staff_names = list(data.keys())  
    return jsonify(staff_names)

@app.route('/get_staff_detail', methods=['POST'])
def get_staff_details():
    team = request.form.get('team')
    role = request.form.get('role')
    staff_name = request.form.get('staff_names') 
    week = request.form.get('week')

    if not week:  
        return jsonify({})  
    try:
        year, week_number = map(int, week.split('-W'))
        week_date = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    except ValueError:
        return jsonify({})  

    ref = db.reference(f"sales_performance/{team}/{role}/{staff_name}/{week_date}/weekly_target")
    
    data = ref.get() or {}

    return jsonify(data)

@app.route('/submit_performance', methods=['POST'])
def submit_performance():
    staff_name = request.form.get('staffName')
    team = request.form.get('team')
    role = request.form.get('role')
    posting_date_str = request.form.get('date') 
       
    posting_date = datetime.strptime(posting_date_str, '%Y-%m-%d')
    first_day_of_week = posting_date - timedelta(days=posting_date.weekday())
    weekly_timestamps = first_day_of_week.strftime('%Y-%m-%d')
    
    performance_data = extract_performance_data(request, role)
    db_path = f"sales_performance/{team}/{role}/{staff_name}/{weekly_timestamps}/{posting_date_str}"
    ref = db.reference(db_path)
    ref.set(performance_data)  
    
    team_performance_datas = team_performance_data(team,posting_date_str)
    db_path1 = f"sales_performance/{team}/team/{weekly_timestamps}/{posting_date_str}"
    ref = db.reference(db_path1)
    ref.set(team_performance_datas)
    
    return redirect(url_for('home', success=True))

def extract_performance_data(request, role):
    data = {}
    if role == 'tc':
       
        fields = ['visit_booked', 'leads', 'sales', 'calls', 'not_counted_sale']
        leads = float(request.form.get('leads', 0))
        visit_booked = float(request.form.get('visit_booked', 0))
        if visit_booked:
            lead_to_visit_ratio = (visit_booked / leads) * 100
            data['lead_to_visit'] = lead_to_visit_ratio
        
        sales = float(request.form.get('sales', 0))
        if leads:
            lead_to_sale_ratio = (sales / leads) * 100
            data['lead_to_sale'] = lead_to_sale_ratio
            
    elif role == 'pr':
        fields = ['visits', 'sales', 'points', 'not_counted_sale']
        
        visits = float(request.form.get('visits', 0))
        sales = float(request.form.get('sales', 0))
        if visits:
            visit_to_sale_ratio =(sales / visits) * 100
            
            data['visit_to_sale_ratio'] = visit_to_sale_ratio

    elif role == 'manager':
        fields = ['visit_booked', 'leads', 'sales', 'calls', "visits", "points"]
        
    else:
        fields = request.form.keys()

    for field in fields:
        if request.form.get(field):
            data[field] = request.form.get(field)

    return data

def team_performance_data(team, posting_date_str):
    ref = db.reference(f"sales_performance").child(team)
    data = ref.get()
    total_sales = 0
    total_visits = 0
    total_leads = 0
    total_visit_booked = 0
    total_metrics = {'sales': 0, 'points': 0, 'visits': 0, 'calls': 0, 'leads': 0, 'visit_booked': 0, 'visit_to_sale_ratio': 0, 'not_counted_sale': 0, 'lead_to_sale':0, 'lead_to_visit':0}  # Initialize total metrics counter
    if data is not None:
        for staff, details in data.items():
            staff_metrics = {'sales': 0, 'points': 0, 'visits': 0, 'calls': 0, 'leads': 0, 'visit_booked': 0, 'visit_to_sale_ratio': 0, 'not_counted_sale': 0, 'lead_to_sale':0, 'lead_to_visit':0}  # Initialize metrics counter for each staff member
            for date, info in details.items():
                for name, metrics in info.items():
                    for key, value in metrics.items():
                        if value is not None:  
                            if key == posting_date_str:
                                for metric_name, metric_value in value.items():
                                    if metric_value is not None:  
                                        if metric_name in staff_metrics:
                                            if staff == "tc" and metric_name == 'sales':
                                                continue
                                            else:
                                                staff_metrics[metric_name] += float(metric_value) if metric_name != 'visit_to_sale_ratio' else float(metric_value)
                                                total_metrics[metric_name] += float(metric_value) if metric_name != 'visit_to_sale_ratio' else float(metric_value)
                                                        
            total_sales += staff_metrics['sales']
            total_visits += staff_metrics['visits']
            total_leads += staff_metrics['leads']
            total_visit_booked += staff_metrics['visit_booked']
    else:
        print("No data available")
        
    if total_sales and total_visits:
        total_metrics['visit_to_sale_ratio'] = (total_sales / total_visits)  * 100
    elif total_sales and total_leads:
        total_metrics['lead_to_sale'] = (total_sales / total_leads)  * 100
    elif total_leads and total_visit_booked:
        total_metrics['lead_to_visit'] = (total_visit_booked / total_leads)  * 100
   
    return total_metrics

@app.route('/weeky_team_target', methods=['POST'])
def weeky_team_target():
    team = request.form.get('team')
    points = request.form.get('points')
    sales = request.form.get('sales')
    visits = request.form.get('visits')
    week = request.form.get('week')
    
    year, week_number = map(int, week.split('-W'))
    week_date = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    
    weekly_target = {
        "points": points,
        "sales": sales,
        "visits": visits
    }

    db_path = f"sales_performance/{team}/team/{week_date}/weekly_target"
    ref = db.reference(db_path)
    ref.set(weekly_target)
    return redirect(url_for('home'))
    
    
###################### Details Page ######################
    
@app.route('/details')
def details():
    return render_template("details.html")

###### Get List Of Team Names ######
@app.route('/get_teamname')
def get_teamname():
    ref = db.reference(f"sales_performance")
    team_details = ref.get() or {}
    teams =[]
    for team_name, team_details in team_details.items():
        teams.append(team_name)
    return teams

def get_week_number(date_string):
    date_object = datetime.strptime(date_string, "%Y-%m-%d")
    year = date_object.strftime("%Y")
    week_number = date_object.isocalendar()[1]
    return f"{year}-W{week_number}"

###### Get List of weeks ######
@app.route('/team_data', methods=['POST'])
def get_teamdata():
    team = request.form.get('team')
    
    ref = db.reference(f"sales_performance/{team}/team")
    team_details = ref.get() or {}
    
    keys_and_weeks = {}
    for date_str in team_details:
        
        week_number = get_week_number(date_str)
        keys_and_weeks[week_number] = team_details[date_str]
    return jsonify({"datas": keys_and_weeks})

###### Get Specific Team PR and TC Details ######
@app.route('/gettop_pr_tc', methods=['POST'])
def gettop_pr_tc():
    team = request.form.get('team')
    role = request.form.get('role')
    week = request.form.get('week')
    
    year, week_number = map(int, week.split('-W'))
    week_start_date = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    week_end_date = week_start_date + timedelta(days=6)  

    ref = db.reference(f"sales_performance/{team}/{role}")
    data = ref.get()
    
    if not data:
        return jsonify({}) 
    
    sorted_response = {}

    for staff, dates_data in data.items():
        total_sales = 0
        total_points = 0
        total_visits = 0
        total_not_counted_sales = 0
        total_calls = 0  
        total_leads = 0  
        total_visit_booked = 0  
        visit_to_sale_ratio = 0
        lead_to_sale = 0

        for date_str, date_data in dates_data.items():
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if week_start_date <= current_date <= week_end_date:
                for data_key, data_value in date_data.items():
                    if role == 'pr':
                        if data_key != 'weekly_target':  
                            if isinstance(data_value, dict):
                                if 'sales' in data_value:
                                    total_sales += float(data_value['sales'])
                                if 'points' in data_value:
                                    total_points += float(data_value['points'])
                                if 'visits' in data_value:
                                    total_visits += float(data_value['visits'])
                                if 'not_counted_sale' in data_value:
                                    total_not_counted_sales += float(data_value['not_counted_sale'])
                                if 'visit_to_sale_ratio' in data_value:
                                    visit_to_sale_ratio += float(data_value['visit_to_sale_ratio'])
                    elif role == 'tc':
                        if isinstance(data_value, dict):
                            if 'calls' in data_value:
                                total_calls += float(data_value['calls'])
                            if 'leads' in data_value:
                                total_leads += float(data_value['leads'])
                            if 'sales' in data_value:
                                total_sales += float(data_value['sales'])
                            if 'visit_booked' in data_value:
                                total_visit_booked += float(data_value['visit_booked'])
                            if 'lead_to_sale' in data_value:
                                lead_to_sale += float(data_value['lead_to_sale'])
       
        sorted_response[staff] = {
            'weekly_data': {
                'sales': total_sales,
                'points': total_points,
                'visits': total_visits,
                'not_counted_sales': total_not_counted_sales,
                'calls': total_calls,  
                'leads': total_leads, 
                'visit_booked': total_visit_booked,
                'visit_to_sale_ratio': visit_to_sale_ratio,
                'lead_to_sale': lead_to_sale    
            },
            'week_start_date': week_start_date.isoformat(),
            'week_end_date': week_end_date.isoformat()
        }
        
    sorted_response = dict(sorted(sorted_response.items(), key=lambda x: x[1]['weekly_data']['sales'], reverse=True))
    
    return jsonify(sorted_response)

###### Get All Team PR and TC Details ######
@app.route('/gettop_pr_tc_all_teams', methods=['POST'])
def gettop_pr_tc_all_teams():
    role = request.form.get('role')
    week = request.form.get('week')
    year, week_number = map(int, week.split('-W'))
    week_start_date = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    week_end_date = week_start_date + timedelta(days=6)  

    sorted_response = {}
    teams_ref = db.reference(f"sales_performance")
    teams = teams_ref.get()
    
    if not teams:
        return jsonify({}) 
    
    for team, roles_data in teams.items():
        if role in roles_data:  
            data = roles_data[role]
            for staff, dates_data in data.items():
                weekly_data = {
                    'sales': 0,
                    'points': 0,
                    'visits': 0,
                    'not_counted_sales': 0,
                    'calls': 0,
                    'leads': 0,
                    'visit_booked': 0,
                    'visit_to_sale_ratio' : 0,
                    'lead_to_sale' : 0
                }

                for date_str, date_data in dates_data.items():
                    current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if week_start_date <= current_date <= week_end_date:
                        for data_key, data_value in date_data.items():
                            if role == 'pr' and data_key != 'weekly_target':
                                for key in weekly_data:
                                    if key in data_value:
                                        value = float(data_value[key])
                                        if value.is_integer():
                                            weekly_data[key] = "{:.0f}".format(value)  # Format as integer
                                        else:
                                            weekly_data[key] = "{:.1f}".format(value)  # Format with one decimal point
                            elif role == 'tc':
                                for key in weekly_data:
                                    if key in data_value:
                                        value = float(data_value[key])
                                        if value.is_integer():
                                            weekly_data[key] = "{:.0f}".format(value)  # Format as integer
                                        else:
                                            weekly_data[key] = "{:.1f}".format(value)  # Format with one decimal point

                sorted_response.setdefault(team, {}).setdefault('weekly_data', {}).update({
                    staff: weekly_data
                })

    return jsonify(sorted_response)

###### Get Team Datas ######
@app.route('/get_topteam', methods=['POST'])
def top_team():
    week = request.form.get('week')
    if not week:
        return jsonify({"error": "Week parameter is missing"}), 400

    year, week_number = map(int, week.split('-W'))
    week_start_date = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    teams_ref = db.reference(f"sales_performance")
    teams = teams_ref.get()

    if not teams:
        return jsonify({"error": "No data found in 'sales_performance'"}), 404

    week_data = {}
    for team, team_data in teams.items():
        if 'team' in team_data:
            team_info = team_data['team']
            team_week_data = defaultdict(int)  
            for date_str, data in team_info.items():
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if week_start_date <= date < week_start_date + timedelta(days=7):
                    
                    for value_dict in data.values():
                        for key, value in value_dict.items():
                            if isinstance(value, (int, float)):  
                                team_week_data[key] += value
            week_data[team] = dict(team_week_data)  # Convert defaultdict to regular dictionary
    return jsonify(week_data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
