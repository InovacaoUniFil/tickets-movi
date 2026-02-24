from flask import Flask, redirect, url_for, render_template, request, session
import json
import requests
import time
import os
import random
from dotenv import load_dotenv
load_dotenv()

movi_url = 'https://unifil.movidesk.com/'
movi_api_url = movi_url+'public/v1/'

movi_token = 'token=478d1b60-5efc-461c-898b-953d7148bdf9'

UPLOAD_FOLDER = './SaveFolder'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1000 * 1000

apoio_subjects = [
    "Financeiro",
    "Disciplinas não Disponibilizadas",
    "Notas Divergentes",
    "Prazo das Atividades",
    "Dúvidas sobre Provas (Presencial)",
    "Dúvidas/Problemas no Portal do Aluno",
    "Dúvidas/Problemas no Ambiente Virtual de Aprendizagem",
    "Solicitação de Certificado",
    "Outros"
]

def create_new_user(cpf,name,email):
    print("create_new_user")
    movi_person_data = {
        'id' : str(cpf),
        'isActive' : True,
        'personType' : 1,
        'profileType' :2,
        'emails' : [{
            'emailType': "Aluno",
            'email': str(email),
            'isDefault': True
            }],
        'cpfCnpj': str(cpf),
        'businessName' : str(name),
        'userName' : str(email),
        'password' : str(cpf),
    }
    print(movi_person_data)
    movi_token = os.environ.get("MOVI_TOKEN")
    user = requests.post(movi_api_url+'persons?'+movi_token, json = movi_person_data)
    time.sleep(0.5)
    print("created user")
    while True:
        user = requests.get(movi_api_url+'persons?'+movi_token+'&id='+str(cpf))
        if user.status_code!=404:
            break
        time.sleep(0.5)
    return json.loads(user.content)

def create_tutor_user(cpf,name,email,course_name):
    print("create_tutor_user")
    if email == None:
        email = cpf
    movi_person_data = {
        'id' : cpf,
        'isActive' : True,
        'personType' : 1,
        'profileType' :1,
        'accessProfile' :"Tutores",
        'businessName' : str(name),
        'userName' : str(email),
        'password' : str(cpf),
        'teams': ["Curso - "+str(course_name)]
    }
    movi_token = os.environ.get("MOVI_TOKEN")
    course = requests.post(movi_api_url+'persons?'+movi_token, json = movi_person_data)
    print("create Tutor" + str(course))
    time.sleep(0.5)
    return json.loads(course.content)

#Legado, não usar devido a limite de agentes
def create_course_user(id_curso,name):
    print("create_course_user")
    movi_person_data = {
        'id' : str(id_curso),
        'isActive' : True,
        'personType' : 1,
        'profileType' :1,
        'accessProfile' :"Tutores",
        'businessName' : str(name),
        'userName' : str(name),
        'password' : str(id_curso)+"12345678",
        'teams': ["Curso - "+str(name)]
    }
    movi_token = os.environ.get("MOVI_TOKEN")
    course = requests.post(movi_api_url+'persons?'+movi_token, json = movi_person_data)
    time.sleep(0.5)
    print("Discipline" + str(course))
    return json.loads(course.content)

def create_ticket(user):
    return user

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods = ['POST'])
def hello_world():
    return render_template("index.html", requestData = request.form, error = "")

@app.route("/sendToMovi", methods = ['POST'])
def send_to_movi():
    movi_token = os.environ.get("MOVI_TOKEN")
    #Check if Form is filled or return error
    print("Check if Form is filled or return error")
    if (str(request.form["text_input"]) == "") or (str(request.form["category_type"]) == "") or (str(request.form["subject_type"]) == ""):
        return render_template("index.html", requestData = request.form, error = "Todos os campos são obrigatórios!")

    #Check if user exists or create new user
    print("Check if user exists or create new user")
    user = requests.get(movi_api_url+'persons?'+movi_token+'&id='+str(request.form["custom_user_login"]))
    if(user.status_code==404):
        user = create_new_user(request.form["custom_user_login"],request.form["custom_user_name"],request.form["custom_user_email"])
    else:
        user = json.loads(user.content)
        
    #alimentar Webhook
    print("alimentar Webhook")
    if str(request.form["custom_canvas_course_id"]) != "$Canvas.course.id":
        canvas_token = os.environ.get("CANVAS_TOKEN")
        print(canvas_token)
        enrollment_data = requests.get("https://unifil.instructure.com/api/v1/courses/"+str(request.form["custom_canvas_course_id"])+"/enrollments?access_token="+canvas_token,headers={'Authorization':"Bearer "+canvas_token} ,verify="./static/certs.pem")
        course_data = requests.get("https://unifil.instructure.com/api/v1/courses/"+str(request.form["custom_canvas_course_id"])+"?access_token="+canvas_token,headers={'Authorization':"Bearer "+canvas_token} ,verify="./static/certs.pem")
        print(json.loads(course_data.content))
        if (len(json.loads(enrollment_data.content)) > 0):
            print(json.loads(enrollment_data.content))
            enrollment_data = json.loads(enrollment_data.content)[0]
        else:
            enrollment_data = {"sis_section_id" : "None"}
    else:
        enrollment_data = {"sis_section_id" : "None"}
    print(enrollment_data)
    """
    #Get student Data from Webook
        print("Get student Data from Webook")
        bearer = requests.post("https://webhook.unifil.br/login",headers={"Content-Type": "application/json"},data=json.dumps({"username":"tamadeu","email":"tamadeu@unifil.br","password":"1b396ec5-5b2a-4bcf-88d6-c63800b15408"}) ,verify="./static/certs.pem")
        time.sleep(0.5)
        bearer = json.loads(bearer.content)["token"]
        student_data = requests.get("https://webhook.unifil.br/aluno",headers={'Authorization':"Bearer "+bearer,"Content-Type": "application/json"},data=json.dumps({"sis_section_id" : str(enrollment_data["sis_section_id"]), "cpf" : str(request.form["custom_user_login"]) }) ,verify="./static/certs.pem")
        if(json.loads(student_data.content)["aluno"] == []): return render_template("index.html", requestData = request.form, error ="O seu usuário não foi encontrado no sistema de Ticket, entre em contato com um coordenador/suporte. (Codigo: Erro_de_Webhook:STUDENT_NOT_FOUND)")
        student_data = json.loads(student_data.content)["aluno"][0]
        print(student_data)
        if student_data["nome_aluno"] == None:
            return render_template("index.html", requestData = request.form, error ="Erro: Aluno não cadastrado")
        if len(student_data["nome_curso"]) > 64:
        student_data["nome_curso"] = student_data["nome_curso"][:60]
    """
    ticket_context = ""
    if enrollment_data["sis_section_id"] != "None":
        course_data = json.loads(course_data.content)
        course_code = course_data["course_code"][:3]
        with open('course_tag.json') as f:
            course_tag = json.load(f)
        with open('tutor_data.json') as f:
            tutor_data = json.load(f)
        if course_code in course_tag:
            tutor_id = random.sample(course_tag[course_code]["tutors"],k=1)[0]
            if(not tutor_data[tutor_id]["active"]):
                for t in course_tag[course_code]["tutors"]:
                    tutor_id = t
                    if tutor_data[tutor_id]["active"]:
                        break
            student_data = {
                "cpf_tutor":tutor_id,
                "nome_tutor":tutor_data[tutor_id]["nome"],
                "nome_curso":course_tag[course_code]["name"]
            }
        else:
            ticket_context = "<p style=\"box-sizing: border-box; margin: 0\">Código da Disciplina:" +course_data["course_code"]+"</p><p style=\"box-sizing: border-box; margin: 0\">Nome da Disciplina"+course_data["name"]+"</p>"
            student_data = {
                "cpf_tutor":None,
                "nome_tutor":"Supervisão Tutoria EaD",
                "nome_curso":"Redirecionar"
            }
    else:
        student_data = {
            "cpf_tutor":None,
            "nome_tutor":"Supervisão Tutoria EaD",
            "nome_curso":"Redirecionar"
        }

    #Atrela o Tutor ao Ticket
    owner_name = ""
    owner_team = ""
    category = ""
    if (str(request.form["category_type"]) in apoio_subjects):
        #Ticket do Apoio
        owner_name = "Apoio - Graduação EaD"
        owner_team = "EaD - Apoio"
        category = str(request.form["category_type"])
    else:
        #Ticket Tutoria
        print("Procura o tutor no Sistema")
        if student_data["cpf_tutor"] != None:
            #Com Tutor no Webhook
            tutor = requests.get(movi_api_url+'persons?'+movi_token+'&id='+str(student_data["cpf_tutor"]))
            if tutor.status_code == 404:
                print("Não Encontrado")
                #tutor = create_tutor_user(str(student_data["cpf_tutor"]),str(student_data["nome_tutor"]),str(student_data["email_tutor"]),str(student_data["nome_curso"]))     
                owner_name = "Supervisão Tutoria EaD"
                tutor = requests.get(movi_api_url+'persons?'+movi_token+'&id='+"7U70R")
            else:
                print("Encontrado")
                owner_name = str(student_data["nome_tutor"])
        else:
            #Sem Tutor no Webhook
            owner_name = "Supervisão Tutoria EaD"
            tutor = requests.get(movi_api_url+'persons?'+movi_token+'&id='+"7U70R")
         
        #Se o tutor não esta vinculado à disciplina no Movidesk, vincula o tutor
        tutor = json.loads(tutor.content)
        if ("Curso - "+str(student_data["nome_curso"])) not in tutor["teams"]:
            teams = tutor["teams"].copy()
            teams.append(("Curso - "+str(student_data["nome_curso"])))
            tutor = requests.patch(movi_api_url+'persons?'+movi_token+'&id='+tutor["id"],headers={"Content-Type": "application/json"},data=json.dumps({"teams":teams}))
            time.sleep(0.5)

        owner_team = "Curso - "+str(student_data["nome_curso"])
        category = "Tutoria - " + str(request.form["category_type"])

    #Get subject name from form, if it exists
    print("Get subject name from form, if it exists")
    coursename = str(request.form["custom_canvas_course_name"])
    if len(student_data["nome_curso"]) > 64:
        coursename = str(request.form["custom_canvas_course_name"])[:60]
    if coursename == "$Canvas.course.name":
        coursename = "Nenhuma Disciplina Selecionada"
        
    #Create a Ticket
    print("Create a Ticket")
    movi_ticket_data = {
    "type" : 2,
    "createdBy" : {
        "id" : user["id"],
        "personType" : user["personType"],
        "profileType" : user["profileType"]
    },
    "clients" : [{
        "id" : user["id"],
        "personType" : user["personType"],
        "profileType" : user["profileType"]
    }],
    "owner" : owner_name,
    "ownerTeam" : owner_team,
    "subject" : str(request.form["subject_type"]),
    "category" : category,
    "actions" : [
        {
        "type" : 2,
        "description" : (ticket_context + str(request.form["text_input"]))
        }
    ],
    "customFieldValues" : [
        {
        "customFieldId" : 137236,
        "customFieldRuleId" : 69372,
        "line" : 1,
        "value" : coursename
        },
        {
        "customFieldId" : 137235,
        "customFieldRuleId" : 69373,
        "line" : 1,
        "value" : str("Indisponivel")
        },
    ]
    }
    print(movi_ticket_data)
    ticket_response = requests.post(movi_api_url+'tickets?'+movi_token, json = movi_ticket_data)
    time.sleep(0.5)
    print(ticket_response.content)
    ticket_response = json.loads(ticket_response.content)
    print(ticket_response)
    while True:
        ticket = requests.get(movi_api_url+'tickets?'+movi_token+"&id="+str(ticket_response["id"]))
        if ticket.status_code!=404:
            break
        time.sleep(0.5)

    #Attach a file to a ticket if there is one
    print("Attach a file to a ticket if there is one")
    if('file' in request.files):
        ticket = json.loads(ticket.content)
        action_id = ticket["actions"][0]["id"]
        file = request.files['file']
        if allowed_file(file.filename):
            print(file.filename)
            attach_request = requests.post(movi_api_url+"ticketFileUpload?"+movi_token+"&id="+str(ticket_response["id"])+"&actionId="+str(action_id),files={'file':(file.filename,file)})
    return render_template("sucesso.html",username=str(request.form["custom_user_email"]), password=str(request.form["custom_user_login"]))

@app.route("/loginToMovi", methods = ['POST'])
def login_to_movi():
    return redirect(movi_url+"Account/Authenticate?"+movi_token+"&userName="+str(request.form["username"])+"&password="+str(request.form["password"]))
    
@app.route("/loginNoTicket", methods = ['POST'])
def movi_login_no_ticket():
    return redirect(movi_url+"Account/Authenticate?"+movi_token+"&userName="+str(request.form["custom_user_email"])+"&password="+str(request.form["custom_user_login"]))
