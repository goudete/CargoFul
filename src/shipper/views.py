from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .forms import Order_Form, WeeklyRecurrenceForm
from .models import order, shipper, status_update
from authorization.models import Profile, User_Feedback
from django.http import JsonResponse
from django.core import serializers
from django.urls import reverse
import json
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
import io
from rest_framework.decorators import api_view
from authorization.decorators import allowed_users
import googlemaps
from decimal import Decimal
import math
from haversine import haversine, Unit
from time import sleep
from django.contrib import messages
import environ
import os
from friendship.models import Friend, Follow, Block, FriendshipRequest
from django.contrib.auth.models import User
from DataProcessing.santiModel import pricingModel
from trucker.models import counter_offer
from .recurrence_handlers import getRecurrenceVars, getRecurrenceEndVars, getRecurrenceVarsFromConfirmation, getRecurrenceEndVarsFromConfirmation, saveWeeklyRecurringOrder
from django.core.mail import send_mail, EmailMultiAlternatives
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from trucker.file_storage import FileStorage
import botocore
import boto3
import magic
from CargoFul import settings
from django.template.loader import get_template
from django.template.loader import render_to_string
from io import BytesIO
import zipfile
from botocore.config import Config


# Create your views here.

#for getting sensitive info
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#Environment variables
#https://www.mattlayman.com/building-saas/django-environ-django-debug-toolbar/
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)
env_file = os.path.join(BASE_DIR, ".env")
environ.Env.read_env(env_file)
Google_API = env("GMAPS_API_KEY")

@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST', 'GET'])
def post_order(request):
    #if the method is a POST, then a user is editing an order from the confirmation page
    if request.method == 'POST':
        #for getting number of unread notifications
        me = shipper.objects.get(user = request.user)
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        jsn.pop("csrfmiddlewaretoken") #remove unnecessary stuff
        #getting order specs
        pu_addy, del_addy = jsn['pickup_address'], jsn['delivery_address']
        date, time = jsn['pickup_date'], jsn['pickup_time']
        #format time
        if time != "" and int(time.split(":")[0]) == 12:
            time = str(time) + " PM"
        elif time != "" and int(time.split(":")[0]) > 12:
            time = str(int(time.split(":")[0]) -12) + ":" +str(time.split(":")[1]) + " PM"
        elif time != "":
            time = str(time) + " AM"
        #other specs
        weight = jsn['weight']
        truck, price = jsn['truck_type'], jsn['price']
        contents, instructions = jsn['contents'], jsn['instructions']
        #get orden de embarco file
        # orden_de_embarco = request.FILES['orden_de_embarco']
        #render a copy of order form (different HTML file b/c there is no crispy forms)
        TRUCK_TYPES = [
        ('Low Boy', 'Low Boy'),
        ('Caja Seca 48 pies', 'Caja Seca 48 pies'),
        ('Refrigerado 48 pies', 'Refrigerado 48 pies'),
        ('Plataforma 48 pies', 'Plataforma 48 pies'),
        ('Caja Seca 53 pies', 'Caja Seca 53 pies'),
        ('Refrigerado 53 pies', 'Refrigerado 53 pies'),
        ('Plataforma 53 pies', 'Plataforma 53 pies'),
        ('Full Caja Seca', 'Full Caja Seca'),
        ('Full Refrigerado','Full Refrigerado'),
        ('Full Plataforma', 'Full Plataforma'),
        ('Torton Caja Seca', 'Torton Caja Seca'),
        ('Torton Refrigerado', 'Torton Refrigerado'),
        ('Torton Plataforma', 'Torton Plataforma'),
        ('Rabon Caja Seca', 'Rabon Caja Seca'),
        ('Rabon Refrigerado', 'Rabon Refrigerado'),
        ('Rabon Plataforma', 'Rabon Plataforma'),
        ('Camioneta 5.5 tons Seca', 'Camioneta 5.5 tons Seca'),
        ('Camioneta 5.5 tons Refrigerada','Camioneta 5.5 tons Refrigerada'),
        ('Camioneta 5.5 tons Plataforma','Camioneta 5.5 tons Plataforma'),
        ('Camioneta 3.5 tons Seca', 'Camioneta 3.5 tons Seca'),
        ('Camioneta 3.5 tons Refrigerada','Camioneta 3.5 tons Refrigerada'),
        ('Camioneta 3.5 tons Redila', 'Camioneta 3.5 tons Redila'),
        ('Camioneta 1.5 tons Seca', 'Camioneta 1.5 tons Seca'),
        ('Camioneta 1.5 tons Refrigerada', 'Camioneta 1.5 tons Refrigerada'),
        ('Camioneta 1.5 tons Redila','Camioneta 1.5 tons Redila')
        ] #this dict is for the dropdown menu for truck type
        return render(request, 'shipper/change_order.html',
        {
            'pu_addy': pu_addy,
            'del_addy': del_addy,
            'date': date,
            'time': time,
            'truck': truck,
            'truck_dict': TRUCK_TYPES,
            'price': price,
            'weight': weight,
            'contents': contents,
            'instructions': instructions,
            'g_api': Google_API,
            'num_notifications': num_notifications
        })
    #if the method is a get then the user is posting a new order for the first time
    else:
        order_form = Order_Form()
        #for getting number of unread notifications
        me = shipper.objects.get(user = request.user)
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
    return render(request, 'shipper/post_order.html', {'form': order_form, 'g_api': Google_API, 'num_notifications': num_notifications})

#display shipper dashboard
@login_required
@allowed_users(allowed_roles=['Shipper'])
def see_dashboard(request):
    #first check that request is a GET
    if request.method == "GET":
        #for getting number of unread notifications
        me = shipper.objects.get(user = request.user)
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        company = shipper.objects.filter(user = request.user).first() #this query gets the shipper
        set = order.objects.filter(shipping_company = company).exclude(status = 4).exclude(status = 5).order_by('status') #this query gets all jobs posted by the user in order from status 2, 3 (excludes delivered and cancelled)
        return render(request, 'shipper/dashboard.html', {'set': set, 'company' : company, 'num_notifications': num_notifications})

#intermediate confirmation step, once a shipper submits an order, they are sent here to confirm
@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST'])
def confirm(request):
    if request.method == "POST":
        #for getting number of unread notifications
        me = shipper.objects.get(user = request.user)
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        """stuff for handling json inside request"""
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        #get necessary info
        #use googlemaps api to get lat and long for pickup and delivery
        gmaps = googlemaps.Client(key=Google_API)
        pu_address_full = jsn['pu_addy']
        del_address_full = jsn['del_addy']
        pu_geocode = gmaps.geocode(pu_address_full)
        del_geocode = gmaps.geocode(del_address_full)
        #get lat  and lng
        pu_lat = pu_geocode[0]['geometry']['location']['lat']
        pu_long = pu_geocode[0]['geometry']['location']['lng']
        del_lat = del_geocode[0]['geometry']['location']['lat']
        del_long = del_geocode[0]['geometry']['location']['lng']

        """lines 86 - 103 are for getting mdpt of two lat/lng coordinates"""
        x,y,z = 0,0,0
        lat1,long1 = math.radians(pu_lat), math.radians(pu_long)
        x += (math.cos(lat1)*math.cos(long1))
        y += (math.cos(lat1)*math.sin(long1))
        z += math.sin(lat1)
        #
        lat2,long2 = math.radians(del_lat), math.radians(del_long)
        x += (math.cos(lat2)*math.cos(long2))
        y += (math.cos(lat2)*math.sin(long2))
        z += math.sin(lat2)
        #avg
        x /= 2
        y/= 2
        z/= 2
        #get mdpts in radians
        mdpt_long = math.degrees(math.atan2(y,x))
        mdpt_sqrt = math.sqrt(x*x + y*y)
        mdpt_lat = math.degrees(math.atan2(z, mdpt_sqrt))
        """end mdpt calculation"""
        #get the distance btwn pickup and delivery
        distance = round(haversine((pu_lat,pu_long), (del_lat,del_long)), 4)
        #other regular metrics

        """THIS IS FOR INCLUDING DATE AND TIME, DO NOT DELETE!!!!!!!"""
        if 'include_date' in jsn.keys():
            date = jsn['pickup_date']
        else:
            date = ""
        if 'include_time' in jsn.keys():
            time = jsn['pickup_time']
        else:
            time = ""
        #account for time being in PM
        if time != "" and time.split(" ")[1] == "PM":
            hour = int(time.split(" ")[0].split(":")[0])
            if hour < 12:
                hour += 12
            time = str(hour) + ":" + time.split(" ")[0].split(":")[1]+" PM"
        """ END of IMPORTANT!!!!! Date and Time block """

        #other specs
        truck = jsn['truck_type']
        cargo = jsn['contents']
        instructions = jsn['instructions']
        price = jsn['price']
        weight = jsn['weight']
        #get recurrence type: Daily, Weekly, Monthly or Yearly. Based on this we get the necessary variables to pass
        # recurrence_type = request.POST.get("recurrence_types", None)
        # recurrence_vars = getRecurrenceVars(recurrence_type,request,jsn)
        # recurrence_end_vars = getRecurrenceEndVars(recurrence_type,request,jsn)
        # print("RECURRENCE END VARS")
        # print(recurrence_end_vars)
        # print("JSON")
        # print(jsn)
        renderDict = {
            'pu_addy': pu_address_full,
            'del_addy': del_address_full,
            'pu_lat': pu_lat,
            'pu_long': pu_long,
            'del_lat': del_lat,
            'del_long': del_long,
            'mid_lat': mdpt_lat,
            'mid_long': mdpt_long,
            'distance': distance,
            'date':date,
            'time': time,
            'truck': truck,
            'cargo': cargo,
            'instruct': instructions,
            'price': price,
            'weight': weight,
            'num_notifications': num_notifications
        #    'recurrence_type': recurrence_type
        }
        # for key in recurrence_vars:
        #     renderDict[key] = recurrence_vars[key]
        # for key in recurrence_end_vars:
        #     renderDict[key] = recurrence_end_vars[key]
        # if "recurrence_indicator" in jsn:
        #     renderDict["recurrence_indicator"] = '1'
        # else:
        #     renderDict["recurrence_indicator"] = '0'
    else:
        pass
    #long list of variables is for the html page, all of these will be displayed in the confirmation page
    return render(request, 'shipper/confirmation.html',renderDict)

#if the order is confirmed, then this sends the user to upload the orden de embarco
@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST'])
def order_success(request):
    #check if request is a post
    if request.method == "POST":
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        jsn.pop('csrfmiddlewaretoken')
        return render(request, 'shipper/include_orden_de_embarco.html', {'jsn':jsn})

#this is the view that creates the order, it either gets an orden de embarco assigned to it or not
@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def upload_orden_de_embarco_from_order(request):
    jdp = json.dumps(request.POST) #get request into json form
    jsn = json.loads(jdp) #get dictionary from json
    jsn.pop("csrfmiddlewaretoken") #remove unnecessary stuff
    #geocode stuff
    pu_lat, pu_long = jsn['pickup_latitude'], jsn['pickup_longitude']
    del_lat, del_long = jsn['delivery_latitude'], jsn['delivery_longitude']
    #address stuff
    pu_address, del_address = jsn['pickup_address'], jsn['delivery_address']
    #distance
    dist = float(jsn['distance'])
    #create the customer_order_no field
    id = request.user.id
    ship = shipper.objects.filter(user = request.user).first()
    num_orders = len(order.objects.filter(shipping_company = ship))+1
    customer_order_no = 'CF'+str(id)+"-"+str(num_orders)
    #save order
    n_order = Order_Form(request.POST)
    if n_order.is_valid():
        new_order = n_order.save(commit = False)
        company = shipper.objects.filter(user = request.user).first()
        new_order.customer_order_no = customer_order_no
        new_order.shipping_company = company
        new_order.pickup_latitude = pu_lat
        new_order.pickup_longitude = pu_long
        new_order.delivery_latitude = del_lat
        new_order.delivery_longitude = del_long
        new_order.pickup_address = pu_address
        new_order.delivery_address = del_address
        new_order.distance = round(dist,2)
        new_order.save()
        #save carta porte to S3
        if 'orden_de_embarco' in request.FILES:
            files_dir = 'docs/{order}'.format(order = "order" +str(new_order.id))
            file_storage = FileStorage()
            doc = request.FILES['orden_de_embarco'] #get file
            mime = magic.from_buffer(doc.read(), mime=True).split("/")[1]
            doc_path = os.path.join(files_dir, "orden_de_embarco."+mime) #set path for file to be stored in
            new_order.orden_de_embarco.name = doc_path
            new_order.save()
            file_storage.save(doc_path, doc)
            #save doc to order's orden de embarco file
        messages.info(request, _("Order ") + str(customer_order_no) + _(" Placed Successfully"))
        #notify truckers per email
        connected_truckers = Friend.objects.friends(request.user) #get truckers which are connected to shipper
        for trucker in connected_truckers:
            email = trucker.email
            username = trucker.username
            subject, from_email, to = 'Tenemos una oportunidad para ti', settings.EMAIL_HOST_USER, email
            text_content = render_to_string('emails/new_opportunity/new_opportunity_ES_txt.html', {
            'username': username,
            })
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            html_template = get_template("emails/new_opportunity/new_opportunity_ES.html").render({
                                        'username': username,
                                        })
            msg.attach_alternative(html_template, "text/html")
            msg.send()

    else:
        print('invalid!')

    return HttpResponseRedirect("/shipper")

@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST', 'GET'])
def show_truckers(request):
    if request.method == "POST":
        #for getting number of unread notifications
        me = shipper.objects.get(user = request.user)
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        query = jsn['query'] #what was queried in searchbar
        #get a query set of truckers for the searchbar
        connection_list = Friend.objects.friends(request.user) #list of ppl user already connected with
        pending_connects = Friend.objects.sent_requests(user=request.user)  #list of connections you have sent
        pending = [] #the list of recipients of the connects in pending_connects
        #get the recipients
        for p in pending_connects:
            if Friend.objects.are_friends(request.user, p.to_user):
                continue #if users are already friends disregard
            elif p in Friend.objects.rejected_requests(user=p.to_user):
                continue #if user rejected connection disregard
            else:
                pending.append(p.to_user)
        #get the ppl whose company names match your query
        query_set = []
        queries = query.split(" ") #turns a search like "trucking company" -> [trucking, company]
        for word in queries:
            truckers = Profile.objects.filter(user_type = "Trucker").filter(company_name__icontains = word).distinct() #get truckers that have any of the words in company name
            for trucker in truckers:
                query_set.append(trucker)
        return render(request, 'shipper/search_connections.html', {'truckers': set(query_set), 'connects': connection_list, 'pending': pending, 'num_notifications': num_notifications})
    else:
        #for getting number of unread notifications
        me = shipper.objects.get(user = request.user)
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        connection_list = Friend.objects.friends(request.user) #list of ppl user already connected with
        pending_connects = Friend.objects.sent_requests(user=request.user)  #list of connections you have sent
        pending = [] #the list of recipients of the connects in pending_connects
        #get the recipients
        for p in pending_connects:
            if Friend.objects.are_friends(request.user, p.to_user):
                continue #if users are already friends disregard
            elif p in Friend.objects.rejected_requests(user=p.to_user):
                continue #if user rejected connection disregard
            else:
                pending.append(p.to_user)
        truckers = Profile.objects.filter(user_type = "Trucker")
        return render(request, 'shipper/search_connections.html', {'truckers': set(truckers), 'connects': connection_list, 'pending': pending, 'num_notifications': num_notifications})

def ajax_price_calculation(request):
    pu_address_full = request.GET.get('puAddy', None)
    del_address_full = request.GET.get('delAddy', None)
    truck_type = request.GET.get('truck_type', None)

    gmaps = googlemaps.Client(key=Google_API)
    pu_geocode = gmaps.geocode(pu_address_full)
    #get lat  and lng
    pu_lat = pu_geocode[0]['geometry']['location']['lat']
    pu_long = pu_geocode[0]['geometry']['location']['lng']

    del_geocode = gmaps.geocode(del_address_full)
    del_lat = del_geocode[0]['geometry']['location']['lat']
    del_long = del_geocode[0]['geometry']['location']['lng']

    "the following code gets the city name from the geocode, needed for pricing algorithm"
    pu_address_components = pu_geocode[0]['address_components']
    for dict in pu_address_components:
        if 'administrative_area_level_1' in dict['types']:
            pu_state_name = dict['long_name']
            break
    del_address_components = del_geocode[0]['address_components']
    for dict in del_address_components:
        if 'administrative_area_level_1' in dict['types']:
            del_state_name = dict['long_name']
            break

    """lines 86 - 103 are for getting mdpt of two lat/lng coordinates"""
    x,y,z = 0,0,0
    lat1,long1 = math.radians(pu_lat), math.radians(pu_long)
    x += (math.cos(lat1)*math.cos(long1))
    y += (math.cos(lat1)*math.sin(long1))
    z += math.sin(lat1)
    #
    lat2,long2 = math.radians(del_lat), math.radians(del_long)
    x += (math.cos(lat2)*math.cos(long2))
    y += (math.cos(lat2)*math.sin(long2))
    z += math.sin(lat2)
    #avg
    x /= 2
    y/= 2
    z/= 2
    #get mdpts in radians
    mdpt_long = math.degrees(math.atan2(y,x))
    mdpt_sqrt = math.sqrt(x*x + y*y)
    mdpt_lat = math.degrees(math.atan2(z, mdpt_sqrt))
    """end mdpt calculation"""
    #get the distance btwn pickup and delivery
    distance = round(haversine((pu_lat,pu_long), (del_lat,del_long)), 4)

    #price = round(float(calculatePrice(distance,'Ciudad de México','Ciudad de México',
    #                            pu_city_name,del_city_name,truck_type)))
    price = pricingModel.calculatePrice(distance,'Aguascalientes','Aguascalientes',truck_type,
                                        float(pu_lat),float(pu_long),float(del_lat),float(del_long))
    price = round(price,-1) #round to nearest unit of ten. e.g. 46 --> 50
    data = {
        'distance':distance,
        'price': price,
        'pu_state_name': pu_state_name,
        'del_state_name': del_state_name,
        # 'pu_city_coords': (pu_lat,pu_long),
        # 'del_city_coords':(del_lat,del_long)
    }
    return JsonResponse(data)

@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST'])
def make_connection_request(request):
    jdp = json.dumps(request.data) #get request into json form
    jsn = json.loads(jdp) #get dictionary from json
    receiver = User.objects.filter(id = jsn['trucker_id']).first() #get recipient of request
    sender = request.user
    Friend.objects.add_friend(sender, receiver) #send 'friend request' which in this case is a connection request
    messages.info(request, _("Requested Connection With ")+ str(receiver.profile.company_name))
    return HttpResponseRedirect('/shipper')

@login_required
@allowed_users(allowed_roles=['Shipper'])
def show_connects(request):
    #for getting number of unread notifications
    me = shipper.objects.get(user = request.user)
    connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
    status_updates = status_update.objects.filter(shipper = me).filter(read = False)
    counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
    num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
    #end notification number
    connections = list(Friend.objects.friends(request.user)) #query existing connections
    sent_connects = Friend.objects.sent_requests(user=request.user)  #list of connections you have sent
    pending = [] #the list of recipients of the connects in pending_connects
    #get the recipients
    for p in sent_connects:
        if Friend.objects.are_friends(request.user, p.to_user):
            continue #if users are already friends disregard
        elif p in Friend.objects.rejected_requests(user=p.to_user):
            continue #if user rejected connection disregard
        else:
            connections.append(p.to_user)
            pending.append(p.to_user)
    query_set = [] #empty list (will be filled by shippers if the following if statement is true)
    if request.method == "POST" and "specific_search" in request.POST:
        #if this is true, then the trucker is searching for someone within his connections list
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        query = jsn['query'] #what was queried in searchbar
        #get the ppl whose company names match your query
        queries = query.split(" ") #turns a search like "trucking company" -> [trucking, company]
        for word in queries:
            truckers = Profile.objects.filter(user_type = "Trucker").filter(company_name__icontains = word).distinct() #get truckers that have any of the words in company name
            for trucker in truckers:
                query_set.append(trucker.user)
    else:
        query_set = connections+pending
    return render(request, 'shipper/connects.html', {'pending': pending, 'connections': connections, 'num_notifications': num_notifications, 'query_set': query_set})

@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST'])
def accept_request(request):
    if request.method == 'POST':
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        req = FriendshipRequest.objects.get(id = jsn['request_id'])
        req.accept()
        Follow.objects.add_follower(request.user, req.from_user)
        messages.info(request, _("Connection from ") + str(req.from_user.profile.company_name) + _(" Accepted"))
        return HttpResponseRedirect('/shipper/notifications')

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def deny_request(request):
    if request.method == 'POST':
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        req = FriendshipRequest.objects.get(id = jsn['request_id'])
        req.reject()
        req.delete()
        return HttpResponseRedirect('/shipper/notifications')

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['GET'])
def show_notifications(request):
    if request.method == "GET":
        me = shipper.objects.get(user = request.user)
        #for getting number of unread notifications
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        #changes in order status will go here
        return render(request, 'shipper/notifications.html', {'requests': connect_requests, 'status_updates': status_updates, 'counter_offers': counter_offers, 'num_notifications': num_notifications})

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def read_status_update(request):
    if request.method == "POST":
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        s_u = status_update.objects.get(id = jsn['status_id']) #get status_update object
        s_u.read = True
        s_u.save()
        return HttpResponseRedirect("/shipper/notifications")

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def accept_counter_offer(request):
    if request.method == "POST":
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        c_offer = counter_offer.objects.get(id = jsn['counter_offer_id'])
        trucker = c_offer.trucker_user
        cur_order = c_offer.order
        #assign trucker to order
        cur_order.truck_company = trucker
        cur_order.status = 2
        cur_order.price = c_offer.counter_price
        cur_order.save()
        #update notification status
        c_offer.status = 2
        c_offer.save()

        #send trucker an email to let them know offer has been accepted
        email = trucker.user.email
        username = trucker.user.username
        send_mail(
        'Counter Offer Accepted!', #email subject
        'Congratulations, ' + username + '! Your counter-offer for a delivery has been accepted. Log on now at http://34.216.209.104/accounts/login/', #email content
        'help@cargoful.org',
        [email],
        fail_silently = False,
        )
        #redirect
        return HttpResponseRedirect("/shipper/notifications")

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def deny_counter_offer(request):
    if request.method == "POST":
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        c_offer = counter_offer.objects.get(id = jsn['counter_offer_id'])
        #update notification status
        c_offer.status = 1
        c_offer.save()
        #redirect
        return HttpResponseRedirect("/shipper/notifications")

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def review_counter_offer(request):
    if request.method == "POST":
        me = shipper.objects.get(user = request.user)
        #for getting number of unread notifications
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        #get counter offer and order objects
        c_offer = counter_offer.objects.get(id = jsn['counter_offer_id'])
        c_offer_order = order.objects.get(id = jsn['counter_offer_order_id'])
        #get stuff about order to show shipper
        """lines 537 - 555 are for getting mdpt of two lat/lng coordinates"""
        x,y,z = 0,0,0
        lat1,long1 = math.radians(c_offer_order.pickup_latitude), math.radians(c_offer_order.pickup_longitude)
        x += (math.cos(lat1)*math.cos(long1))
        y += (math.cos(lat1)*math.sin(long1))
        z += math.sin(lat1)
        #
        lat2,long2 = math.radians(c_offer_order.delivery_latitude), math.radians(c_offer_order.delivery_longitude)
        x += (math.cos(lat2)*math.cos(long2))
        y += (math.cos(lat2)*math.sin(long2))
        z += math.sin(lat2)
        #avg
        x /= 2
        y/= 2
        z/= 2
        #get mdpts in radians
        mdpt_long = math.degrees(math.atan2(y,x))
        mdpt_sqrt = math.sqrt(x*x + y*y)
        mdpt_lat = math.degrees(math.atan2(z, mdpt_sqrt))
        """end mdpt calculation"""
        return render(request, 'shipper/review_counter_offer.html', {"counter":c_offer, "order": c_offer_order, "mdpt_long": mdpt_long, "mdpt_lat": mdpt_lat})

"""this method is almost the same as review_counter_offer, except this one does not have the feature of accepting or denying a counter offer"""
@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def review_my_order(request):
    if request.method == "POST":
        me = shipper.objects.get(user = request.user)
        #for getting number of unread notifications
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        #get counter offer and order objects
        cur_order = order.objects.get(id = jsn['order_id'])
        #get stuff about order to show shipper
        """lines 537 - 555 are for getting mdpt of two lat/lng coordinates"""
        x,y,z = 0,0,0
        lat1,long1 = math.radians(cur_order.pickup_latitude), math.radians(cur_order.pickup_longitude)
        x += (math.cos(lat1)*math.cos(long1))
        y += (math.cos(lat1)*math.sin(long1))
        z += math.sin(lat1)
        #
        lat2,long2 = math.radians(cur_order.delivery_latitude), math.radians(cur_order.delivery_longitude)
        x += (math.cos(lat2)*math.cos(long2))
        y += (math.cos(lat2)*math.sin(long2))
        z += math.sin(lat2)
        #avg
        x /= 2
        y/= 2
        z/= 2
        #get mdpts in radians
        mdpt_long = math.degrees(math.atan2(y,x))
        mdpt_sqrt = math.sqrt(x*x + y*y)
        mdpt_lat = math.degrees(math.atan2(z, mdpt_sqrt))
        """end mdpt calculation"""
        return render(request, 'shipper/review_my_order.html', {"order": cur_order, "mdpt_long": mdpt_long, "mdpt_lat": mdpt_lat})

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['GET'])
def show_past_orders(request):
    if request.method == "GET":
        me = shipper.objects.get(user = request.user)
        #for getting number of unread notifications
        connect_requests = FriendshipRequest.objects.filter(to_user=request.user) #query pending connections
        status_updates = status_update.objects.filter(shipper = me).filter(read = False)
        counter_offers = counter_offer.objects.filter(order__shipping_company__user = request.user).filter(status = 0)
        num_notifications = len(list(connect_requests)) + len(list(status_updates)) + len(list(counter_offers))
        #end notification number
        past_orders = order.objects.filter(shipping_company = me).filter(status = 4)
        return render(request, 'shipper/past_orders.html', {'set': past_orders})

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def get_feedback(request):
    if request.method == "POST":
        jdp = json.dumps(request.data) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        jsn.pop("csrfmiddlewaretoken") #remove unnecessary stuff
        user = request.user
        feedback = User_Feedback(user = user, feedback = jsn['feedback'])
        feedback.save()
        messages.info(request, _("Thank you for your feedback!"))

        return HttpResponseRedirect('/shipper')

def contact_form_view(request):
    if request.method == "POST":
        query_dict = request.POST #request.data doesnt work for some reason
        print("testing accessing")
        print(query_dict['name'])


        customer_name = query_dict['name']
        email = query_dict['email']
        phone_number = query_dict['phone_number']
        website = query_dict['website']
        message = query_dict['message']

        out_message = "Hi, " + customer_name + " has contacted the team with the following message: \n \n"
        out_message += message + "\n \n"
        out_message += "Get back to him at " + email + ". \n \n \n"

        user = request.user
        out_message += "Additional user info:  \n \n"
        out_message += "username: " + str(user.username) + "\n"
        out_message += "user type: " + str(user.profile.user_type) + "\n"
        out_message += "registered email: " + str(user.profile.user.email) + "\n"
        if len(website) > 0:
            out_message += "given website: " + website + "\n"
        if len(phone_number) > 0:
            out_message += "given phone number: " + phone_number + "\n"
        send_mail(
        customer_name + ' HAS A NEW HELP REQUEST!', #email subject
        out_message, #email content
        'help@cargoful.org',
        ['help@cargoful.org'],
        fail_silently = False,
        )

        #send another mail confirming help is on the way
        send_mail(
        'Help is on the way!', #email subject
        """Dear """ + customer_name + """, \n
        Thank you for reaching out to the Cargoful team! \n
        We will review your message and get back to you soon. \n \n
        Never alone with Cargoful! \n
        Your Cargoful team \n \n
        Here your request: \n""" + message, #email content
        'help@cargoful.org',
        [email],
        fail_silently = False,
        )
        messages.info(request, "Thanks "+ str(customer_name)
        + "! We have received your message and will get back to you shortly at " + email)
        return HttpResponseRedirect('/shipper')
    else:
        return render(request, 'shipper/contact_form.html')

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def upload_orden_de_embarco(request):
    jdp = json.dumps(request.POST) #get request into json form
    jsn = json.loads(jdp) #get dictionary from json
    jsn.pop("csrfmiddlewaretoken") #remove unnecessary stuff
    cur_order = order.objects.filter(id = jsn['order_id']).first()
    #save carta porte to S3
    files_dir = 'docs/{order}'.format(order = "order" +str(cur_order.id))
    file_storage = FileStorage()
    doc = request.FILES['orden_de_embarco'] #get file
    mime = magic.from_buffer(doc.read(), mime=True).split("/")[1]
    doc_path = os.path.join(files_dir, "orden_de_embarco."+mime) #set path for file to be stored in
    cur_order.orden_de_embarco.name = doc_path
    cur_order.save()
    file_storage.save(doc_path, doc)
    #save doc to order's orden de embarco file
    return HttpResponseRedirect("/shipper")

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def download_carta_porte(request):
    if request.method == "POST":
        s3 = boto3.resource('s3') #setup to get from AWS
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        order_id = jsn['order_id']
        aws_dir = 'docs/order'+str(order_id)
        bucket = s3.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
        objs = bucket.objects.filter(Prefix=aws_dir) #get folder
        for obj in objs:
            path, filename = os.path.split(obj.key)
            if 'carta_porte' in filename:
                orden_de_embarco = obj.get()['Body'].read()
                mimetype = filename.split(".")[1]
                response = HttpResponse(orden_de_embarco, "application/"+str(mimetype))
                response['Content-Disposition'] = 'attachment;filename=orden_de_embarco.%s' % mimetype
                return response
            else:
                pass
        return HttpResponseRedirect('/shipper')

@login_required
@allowed_users(allowed_roles = ['Shipper'])
@api_view(['POST'])
def view_carta_porte(request):
    if request.method == "POST":
        s3 = boto3.resource('s3') #setup to get from AWS
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        order_id = jsn['order_id']
        aws_dir = 'docs/order'+str(order_id)
        bucket = s3.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
        objs = bucket.objects.filter(Prefix=aws_dir) #get folder
        for obj in objs:
            print(obj)
            path, filename = os.path.split(obj.key)
            if 'carta_porte' in filename:
                orden_de_embarco = obj.get()['Body'].read()
                mimetype = filename.split(".")[1]
                response = HttpResponse(orden_de_embarco, "application/"+str(mimetype))
                response['Content-Disposition'] = 'inline;filename=orden_de_embarco.%s' % mimetype
                return response
            else:
                pass
        ReturnHttpResponseRedirect('/shipper')

@login_required
@allowed_users(allowed_roles=['Shipper'])
@api_view(['POST'])
def download_my_docs(request):
    s3 = boto3.resource('s3') #setup to get from AWS
    #setup to download off AWS
    #create folder to store files
    if request.method == "POST":
        jdp = json.dumps(request.POST) #get request into json form
        jsn = json.loads(jdp) #get dictionary from json
        cur_order = order.objects.filter(id = jsn['order_id']).first() #this is if the user wants to download order docs into .zip
        aws_dir = 'docs/{order}'.format(order = "order" +str(cur_order.id))
        zip_file_name = "Order-"+cur_order.customer_order_no+".zip"
    #create zip file
    byte = BytesIO()
    zip = zipfile.ZipFile(byte, "w")
    #download files
    bucket = s3.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
    objs = bucket.objects.filter(Prefix=aws_dir) #get folder
    for obj in objs: #iterate over file objects in folder
        path, filename = os.path.split(obj.key)
        data = obj.get()['Body'].read()
        open(filename, 'wb').write(data)
        zip.write(filename) #write file to zip folder
        os.unlink(filename)
    zip.close()
    resp = HttpResponse(
        byte.getvalue(),
        content_type = "application/x-zip-compressed"
    )
    resp['Content-Disposition'] = 'attachment; filename = %s' % zip_file_name
    return resp
