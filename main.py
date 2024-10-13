from fastapi import FastAPI, Request,Response
from google.auth.transport import requests
from fastapi.staticfiles import StaticFiles
import google.oauth2.id_token
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse,HTMLResponse
from google.cloud import firestore
import starlette.status as status
from typing import Optional
import google.oauth2.id_token
from fastapi.templating import Jinja2Templates



# Define the FastAPI app
app = FastAPI()

# Firestore client
firestore_db = firestore.Client()

# Request adapter for Firebase
firebase_request_adapter = requests.Request()

# Static and templates directories
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")

# Get user from Firestore
def getUserDetails(user_token):
    user = firestore_db.collection('users').document(user_token['user_id'])
    if not user.get().exists:
        user_data = {
            'email': user_token.get('email'),
        }
        firestore_db.collection('users').document(user_token['user_id']).set(user_data)
    return user

def validate_firebase_token(id_token):
    if not id_token:
        return None
    try:
        return google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
        return None
    
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    listOfev = []
    user = None
    if not user_token:
        return templates.TemplateResponse('main.html', {'request': request, 'user_token': None, 'error_message': None, 'user_info': None})
    ev_query = firestore_db.collection('electric_vehicles')
    user = getUserDetails(user_token).get().to_dict()
    for ev in ev_query.stream():
        detailsOfev = ev.to_dict()
        listOfev.append(detailsOfev)    
    return templates.TemplateResponse('main.html', {'request': request, 'user_token': user_token,'listOfev': listOfev,'user':user})

def storeElectricVehicleData(vehicle_data):
    vehicle_ref = firestore_db.collection('electric_vehicles').document()
    vehicle_ref.set(vehicle_data)
    return vehicle_ref


def retrieveEVDetails(ev_identifier):
    ev_collection = firestore_db.collection('electric_vehicles').where('car_id', '==', ev_identifier)
    listOfev = []
    for ev_document in ev_collection.stream():
        detailsOfev = ev_document.to_dict()
        listOfev.append(detailsOfev)  
    return listOfev


@app.post("/add-car", response_class=RedirectResponse)
async def add_electric_vehicle_route(request: Request):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse('/')
    form = await request.form()
    detailsOfev = {
        'car_id': form['car_id'],
        'car_name': form['car_name'],
        'car_brand': form['car_brand'],
        'car_production_year': int(form['car_production_year']),
        'car_battery_capacity': float(form['car_battery_capacity']),
        'car_range': float(form['car_range']),
        'car_price': float(form['car_price']),
        'car_motor_power': float(form['car_motor_power'])
    }
    storeElectricVehicleData(detailsOfev)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

@app.get("/electric-vehicle-details/{ev_identifier}", response_class=HTMLResponse)
async def ev_details(request: Request, ev_identifier: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    emailId = user_token.get('email')
    ev = retrieveEVDetails(ev_identifier)
    return templates.TemplateResponse('electric-vehicle-details.html', {'request': request, 'detailsOfev': ev,'emailId':emailId})



@app.get("/add-carDetails", response_class=HTMLResponse)
async def add_ev_page(request: Request):
    return templates.TemplateResponse("add-car.html", {"request": request})

@app.get("/search-electric-vehicle", response_class=HTMLResponse)
async def search_car(request: Request,name_filter: Optional[str] = None, manufacturer_filter: Optional[str] = None, min_year_filter: Optional[str] = None, max_year_filter: Optional[str] = None, min_battery_size_filter: Optional[str] = None, max_battery_size_filter: Optional[str] = None, min_wltp_range_filter: Optional[str] = None, max_wltp_range_filter: Optional[str] = None, min_cost_filter: Optional[str] = None, max_cost_filter: Optional[str] = None, min_power_filter: Optional[str] = None, max_power_filter: Optional[str] = None):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    query = firestore_db.collection('electric_vehicles')
    if name_filter:
        query = query.where('car_name', '==', name_filter)

    if manufacturer_filter:
        query = query.where('car_brand', '==', manufacturer_filter)

    if max_year_filter:
        query = query.where('car_production_year', '<=', int(max_year_filter)) 

    if min_year_filter:
        query = query.where('car_production_year', '>=', int(min_year_filter))      
    
    if max_battery_size_filter:
        query = query.where('car_battery_capacity', '<=', float(max_battery_size_filter))

    if min_battery_size_filter:
        query = query.where('car_battery_capacity', '>=', float(min_battery_size_filter))    
    
    if max_wltp_range_filter:
        query = query.where('car_range', '<=', float(max_wltp_range_filter)) 

    if min_wltp_range_filter:
        query = query.where('car_range', '>=', float(min_wltp_range_filter))       
    
    if max_cost_filter:
        query = query.where('car_price', '<=', float(max_cost_filter))  

    if min_cost_filter:
        query = query.where('car_price', '>=', float(min_cost_filter))     
    
    if max_power_filter:
        query = query.where('car_motor_power', '<=', float(max_power_filter))

    if min_power_filter:
        query = query.where('car_motor_power', '>=', float(min_power_filter))     
    
    
    evStream = query.stream()
    listOfev = []
    for ev in evStream:
        detailsOfev = ev.to_dict()
        listOfev.append(detailsOfev)
    emailId = user_token.get('email')
    return templates.TemplateResponse('electric-vehicle-details.html', {'request': request, 'detailsOfev': listOfev,'emailId':emailId})

# Delete Electric Vehicle from Firestore
def deleteElectricVehicle(ev_identifier):
    ev_query = firestore_db.collection('electric_vehicles').where('car_id', '==', ev_identifier)
    ev_documents = ev_query.stream()
    for ev_document in ev_documents:
        ev_document.reference.delete()

# Update Electric Vehicle in Firestore
def updateElectricVehicle(ev_identifier, new_vehicle_data):
    ev_query = firestore_db.collection('electric_vehicles').where('car_id', '==', ev_identifier)
    ev_documents = ev_query.stream()
    for ev_document in ev_documents:
        ev_document.reference.update(new_vehicle_data)
        
@app.post('/delete-electric-vehicle/{ev_identifier}', response_class=RedirectResponse)
async def delete_ev_route(request: Request, ev_identifier: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse('/')
    deleteElectricVehicle(ev_identifier)
    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)        


@app.post("/update-electric-vehicle/{ev_identifier}", response_class=RedirectResponse)
async def update_electric_vehicle_route(request: Request, ev_identifier: str):
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    if not user_token:
        return RedirectResponse('/')

    form = await request.form()
    name = form.get('car_name', '')
    manufacturer = form.get('car_brand', '')
    year = int(form.get('car_production_year', ''))
    battery_size = float(form.get('car_battery_capacity', ''))
    wltp_range = float(form.get('car_range', ''))
    cost = float(form.get('car_price', ''))
    power = float(form.get('car_motor_power', ''))
    new_data = {}
    if name:
        new_data['car_name'] = name
    if manufacturer:
        new_data['car_brand'] = manufacturer
    if year:
        new_data['car_production_year'] = year
    if battery_size:
        new_data['car_battery_capacity'] = battery_size
    if wltp_range:
        new_data['car_range'] = wltp_range
    if cost:
        new_data['car_price'] = cost
    if power:
        new_data['car_motor_power'] = power

    updateElectricVehicle(ev_identifier, new_data)
    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

@app.get("/compare", response_class=HTMLResponse)
async def compare_electric_vehicle_page(request: Request):
    return templates.TemplateResponse("compare-electric-vehicles.html", {"request": request})
 

@app.get("/compare-electric-vehicles", response_class=HTMLResponse)
async def compareElectricVehicles(request: Request, electric_vehicle_1: Optional[str] = None, electric_vehicle_2: Optional[str] = None):
    # Check if both electric vehicle IDs are provided
    if not electric_vehicle_1 or not electric_vehicle_2:
        return "Please provide IDs for both Electric Vehicles"
    
    # Retrieve details for EV1
    ev1_query = firestore_db.collection('electric_vehicles').where('car_name', '==', electric_vehicle_1)
    ev1_documents = list(ev1_query.stream())
    ev1_data = ev1_documents[0].to_dict() if ev1_documents else None

    # Retrieve details for EV2
    ev2_query = firestore_db.collection('electric_vehicles').where('car_name', '==', electric_vehicle_2)
    ev2_documents = list(ev2_query.stream())
    ev2_data = ev2_documents[0].to_dict() if ev2_documents else None

    # Return template response
    return templates.TemplateResponse('compare-electric-vehicles.html', {'request': request, 'electric_vehicle_1_data': ev1_data, 'electric_vehicle_2_data': ev2_data})


@app.post("/add-review-electric-vehicle/{ev_identifier}", response_class=RedirectResponse)
async def addReview(request: Request, ev_identifier: str):
    # Retrieving user token from request
    id_token = request.cookies.get("token")
    user_token = validate_firebase_token(id_token)
    
    # Redirecting to home page if user token is not found
    if not user_token:
        return RedirectResponse('/')
    
    
    # Checking if user is authorized to add review
    if user_token.get('email') == "pranu@yopmail.com" :
        # Retrieving form data
        form_data = await request.form()
        review_text = form_data.get('review', '')
        star_rating = int(form_data.get('rating', ''))

        # Validating star rating
        if star_rating < 1 or star_rating > 5:
            return RedirectResponse(f'/electric-vehicle-details/{ev_identifier}', status_code=status.HTTP_400_BAD_REQUEST)

        # Creating a new review dictionary
        new_review = {
            'text': review_text,
            'rating': star_rating,
        }

        # Adding the new review to the database
        addElectricVehicleReview(ev_identifier, new_review)

    # Redirecting to electric vehicle details page
    return RedirectResponse(f'/electric-vehicle-details/{ev_identifier}', status_code=status.HTTP_302_FOUND)


def addElectricVehicleReview(ev_identifier: str, review_type: dict):
    # Querying the Firestore collection for the electric vehicle document
    ev_query = firestore_db.collection('electric_vehicles').where('car_id', '==', ev_identifier)
    ev_documents = ev_query.get()

    # Iterating through the documents (assuming 'id' is unique, so there should be only one document)
    for ev_document in ev_documents:
        # Getting existing reviews
        oldReviews = ev_document.to_dict().get('reviews', [])
        # Adding the new review to the list of reviews
        oldReviews.append(review_type)
        # Calculating the average rating
        total_rating = sum(review['rating'] for review in oldReviews)
        avg_rating = total_rating / len(oldReviews)
        # Updating the electric vehicle document with the new reviews and average rating
        ev_document.reference.update({
            'oldReviews': oldReviews,
            'avgRating': avg_rating
        })
