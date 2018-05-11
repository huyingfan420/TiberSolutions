from django.shortcuts import render
from pyathena import connect
import os
import numpy as np
from dashboard.ConnectSagemaker import invoke_sagemake_endpoint
from decimal import getcontext, Decimal

# set global variables
unique_countries = []
unique_conditions = []
unique_interventions = []
cursor = connect(aws_access_key_id=os.environ["accessKey"],
                 aws_secret_access_key=os.environ["secretKey"],
                 s3_staging_dir='s3://aws-athena-query-results-565635975808-us-east-2/',
                 region_name='us-east-2').cursor()


def index(request):
    return render(request, 'dashboard/index.html')


def home(request):
    global unique_countries, unique_conditions, unique_interventions, cursor
    if len(unique_countries) == 0:
        unique_conditions = np.load('dashboard/templates/npy/conditions_catagories.npy')
        unique_countries = np.load('dashboard/templates/npy/countries_catagories.npy')
        unique_interventions = np.load('dashboard/templates/npy/interventions_catagories.npy')
    if request.method == "GET":
        return render(request, 'dashboard/patient-home.html',
                      {"show": False, "conditions": unique_conditions, "countries": unique_countries,
                       "interventions": unique_interventions})
    if request.method == 'POST':
        condition = request.POST.getlist('health_condition[]')
        gender = request.POST['gender']
        country = request.POST['country']
        intervention = request.POST.getlist('interventions[]')
        facility_num = request.POST['facility_num']
        us_facility = request.POST['us_facility']
        sponsor_num = request.POST['sponsor_num']
        vector = []
        vector.append(int(facility_num))
        if us_facility == 'yes':
            vector.append(1)
        else:
            vector.append(0)
        vector.append(int(sponsor_num))
        vector.append(condition)
        vector.append(intervention)
        vector.append(country)
        print(vector)
        # build condition list
        conditionlist = "("
        for c in condition:
            conditionlist += '\''
            conditionlist += c
            conditionlist += '\''
            conditionlist += ","
        # get rid of the last ,
        conditionlist = conditionlist[0: len(conditionlist) - 1]
        conditionlist += ')'

        query = "select s.nct_id, brief_title, array_agg(distinct adverse_event_term) adverse_event" \
                + " from clinic.studies s" \
                + " join clinic.reported_events r" \
                + " on s.nct_id = r.nct_id" \
                + " join" \
                + " (" \
                + " select nct_id" \
                + "	from clinic.countries" \
                + "	where name = '" + country + "'" \
                + " ) c" \
                + " on s.nct_id = c.nct_id" \
                + " join" \
                + " (" \
                + " select nct_id" \
                + " 	from clinic.browse_conditions" \
                + " 	where downcase_mesh_term in " + conditionlist \
                + " ) bc" \
                + " on s.nct_id = bc.nct_id" \
                + " join" \
                + " (" \
                + "	select nct_id" \
                + " 	from clinic.eligibilities" \
                + " 	where gender = '" + gender + "'" \
                + " ) e" \
                + " on s.nct_id = e.nct_id" \
                + " group by s.nct_id, brief_title" \
                + " limit 10;"
        cursor.execute(query)
        columnNames = ['nct_id', 'brief_title', 'adverse_events']
        attributeLine = []
        for row in cursor:
            attributes = []
            attributes.append(row[0])
            attributes.append(row[1])
            attributes.append(row[2])
            attributeLine.append(attributes)

        endpoint_name = 'yangz5test'
        percentage = invoke_sagemake_endpoint(vector, endpoint_name) * 100

        percentage = Decimal(percentage).quantize(Decimal('0.00'))

        context = {"tablename": 'result table', "columnNames": columnNames, "attributeLine": attributeLine,
                   "show": True, "percentage": percentage, "conditions": unique_conditions,
                   "countries": unique_countries, "interventions": unique_interventions}
        return render(request, 'dashboard/patient-home.html', context)
