from flask import Flask, render_template, request, redirect, flash, redirect, url_for, jsonify, session, escape
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import boto3
import os
import administrador 
import locutor
import concurso
import propuesta
import db as dynamodb
import redis

app = Flask(__name__, static_folder= 'static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'pruebacloud'

REDIS_URL = os.environ.get('redis://sv-elc.gsatmb.ng.0001.use1.cache.amazonaws.com:6379')
store = redis.Redis.from_url('redis://sv-elc.gsatmb.ng.0001.use1.cache.amazonaws.com:6379')

"""
Definición de rutas    
"""
      
@app.route("/")
def index():
    concursos = concurso.obtener_concurso() 
    propuestasporlocutor = propuesta.obtener_Propuesta_por_concurso_por_locutor()
    return render_template("index.html", concursos = concursos['Items'], propuestasporlocutor = propuestasporlocutor['Items'])

@app.route("/sesion")
def sesion():
      return render_template("login.html")

@app.route("/administradores/<string:id>", methods=['GET'])
def administradores(id):
      if 'username' in session:
        username = escape(session['username'])
        visits = store.hincrby(username, 'visits', 1)
        concursos = concurso.obtener_concurso_admon(id)
        propuestasporlocutor = propuesta.obtener_Propuesta_por_concurso_por_locutor_id(id)      
        return render_template("administrador.html", concursos = concursos['Items'], propuestasporlocutor = propuestasporlocutor['Items'], id =id)        
      return 'You are not logged in'

@app.route("/propuestas/<string:id>", methods=['GET'])
def propuestas(id):
      return render_template("crearpropuesta.html", id = id)

@app.route("/crearcuenta")
def crearcuenta():
      return render_template("register.html")    
      
@app.route("/crearconcurso/<string:id>", methods=['GET'])
def crearconcurso(id):
      if 'username' in session:
        return render_template("crearconcurso.html", id = id)   
      return 'You are not logged in'
      
@app.route('/crearadministrador', methods=['POST'])
def crearadministrador():
    nombre = request.form["nombre"]
    apellido = request.form["apellido"]
    email = request.form["email"]
    password = request.form["password"]
    password2 = request.form["password2"]
    if password == password2:
      admon = administrador.obtener_admon_por_email(email)
      item = admon['Items']
      if item:
        print ('El correo ya existe')
        return render_template("login.html")
      now = datetime.now()
      dt_string = now.strftime("%d%m%Y%H%M%S")
      administrador.insertar_admon(dt_string,nombre, apellido, email, password)
      return render_template("login.html")
    print ('Las contraseñas son diferentes')
    return render_template("register.html")
    
@app.route("/login", methods=['POST'])
def login():
    email = request.form["email"]
    password = request.form["password"]
    admon = administrador.obtener_admon_por_email(email) 
    item = admon['Items']
    if item and admon['Items'][0]['password']['S']==password:
      id_admon=str(admon['Items'][0]['id_admon']['S'])
      session['username'] = id_admon
      return redirect(url_for("administradores", id = id_admon))
    print ('Usuario o contrasena incorrecta')
    return render_template("login.html")
    
@app.route("/verconcursoadmon/<string:id>", methods=['GET'])
def verconcursoadmon(id):
    if 'username' in session:
      concursos = concurso.obtener_concurso_admon(id) 
      item = concursos['Items']
      if not item:
        return redirect(url_for("administradores", id = id))
      return render_template("modificarconcurso.html", concursos = concursos['Items'])
    return 'You are not logged in'

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect("/")

@app.route("/crearconcurso2", methods=['GET','POST'])
def crearconcurso2():
    id_admon = request.form["id"]
    nombre = request.form["nombre"]
    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    file = request.files["logo"]
    #file.save(os.path.join("static/nfs/logos", dt_string+file.filename))
    s3 = boto3.resource('s3')
    s3.Object('supervoices-bucket', 'logos/'+dt_string+file.filename).put(Body=file, ACL='public-read')
    logo = 'https://supervoices-bucket.s3.amazonaws.com/logos/'+dt_string+file.filename
    url = request.form["url"]
    valida = concurso.obtener_url(url) 
    item = valida['Items']
    if item:    
      print ('URL ya existe')
      return redirect(url_for("crearconcurso", id = id_admon))
    fecha_inicio = request.form["inicio"]
    fecha_fin = request.form["fin"]
    valor = request.form["valor"]
    guion = request.form["guion"]
    recomendacion = request.form["recomendacion"]
    concurso.insertar_concurso(dt_string,nombre,id_admon,logo,url,fecha_inicio,fecha_fin,valor,guion,recomendacion)
    return redirect(url_for("administradores", id = id_admon))

@app.route('/editarconcurso/<string:id>', methods=['GET'])
def editarconcurso(id):
    if 'username' in session:
      concursos = concurso.obtener_concurso_por_id(id) 
      return render_template("editarconcurso.html", concursos = concursos['Items'][0])
    return 'You are not logged in'

@app.route('/editarconcurso2/<string:id>',  methods=['GET', 'POST'])
def editarconcurso2(id):
    concursos = concurso.obtener_concurso_por_id(id) 
    if request.method == 'POST':
      nombre = request.form['nombre']
      now = datetime.now()
      dt_string = now.strftime("%d%m%Y%H%M%S")
      file = request.files["logo"]
      s3 = boto3.resource('s3')
      s3.Object('supervoices-bucket', 'logos/'+dt_string+file.filename).put(Body=file, ACL='public-read')
      logo = 'https://supervoices-bucket.s3.amazonaws.com/logos/'+dt_string+file.filename
      url = request.form["url"]
      valida = concurso.obtener_url(url) 
      item = valida['Items']
      if item:  
        print ('URL ya existe')
        return redirect(url_for("editarconcurso", id = id))
      fecha_inicio = request.form['inicio']
      fecha_fin = request.form['fin']
      valor = request.form['valor']
      guion = request.form['guion']
      recomendacion = request.form['recomendacion']
      concurso.actualizar_concurso(id,nombre,logo,url,fecha_inicio,fecha_fin,valor,guion,recomendacion)
    return redirect(url_for("verconcursoadmon", id = concursos['Items'][0]['id_admon']['S']))

@app.route('/eliminarconcurso/<string:id>', methods=['GET'])
def eliminarconcurso(id):
    con = propuesta.obtener_Propuesta_por_concurso(id)
    item = con['Items']
    for pro in item :
      propuesta.eliminar_Propuesta(pro['id_propuesta']['S'])
    admon = concurso.obtener_concurso_por_id(id)
    concurso.eliminar_concurso(id)
    return redirect(url_for("verconcursoadmon", id = admon['Items'][0]['id_admon']['S']))
    
@app.route("/crearlocutor")
def crearlocutor():
    return render_template("index.html")
    
@app.route("/crearpropuesta/<string:id>",methods=['GET','POST'])
def crearpropuesta(id):
    print (id)
    return render_template("crearpropuesta.html", id =id)
# post para subir el audio

@app.route("/subirpropuesta",methods=['GET','POST'])
def subirpropuesta():
  #verificación de locutor por email
    ruta_audio = "https://supervoices-bucket.s3.amazonaws.com/audio_original/"
    email = request.form["email"]
    nombre = request.form["nombre"]
    apellido = request.form["apellido"]
    mensaje = request.form["observacion"]
    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S%f")
    fecha = request.form["fecha"]
    id_concurso = request.form["id_concurso_oculto"]
    estado = "En proceso"
    file = request.files["file"]
    s3 = boto3.resource('s3')
    archivo=file.filename;
    print("nombre audio")
    print(archivo)
    #file.save(os.path.join("static/nfs/audios_originales/", dt_string+file.filename))
    s3.Object('supervoices-bucket', 'audio_original/'+dt_string+archivo).put(Body=file, ACL='public-read')
    client = boto3.resource('sqs')
    queue = client.get_queue_by_name(QueueName='supervoices_sqs')
    response = queue.send_message(MessageBody=dt_string+archivo)
    voz_original = dt_string + file.filename
    voz_convertida = ""
    id_admon = concurso.obtener_concurso_por_id(id_concurso)
    propuesta.insertar_Propuesta(dt_string,fecha,email,id_concurso,estado,voz_original,voz_convertida,mensaje, nombre, apellido, email, id_admon['Items'][0]['id_admon']['S'])
    return render_template("resultadopropuesta.html",message="Hemos recibido tu voz y la estamos procesando para que sea publicada en la página del concurso y pueda ser posteriormente revisada por nuestro equipo de trabajo. Tan pronto la voz quede publicada en la página del concurso te notificaremos por email.")

@app.route("/convertirvoz")
def convertirvoz():
    return render_template("index.html")
    
@app.route("/modificarpropuesta")
def modificarpropuesta():
    return render_template("index.html")
    
@app.route("/enviarcorreo")
def enviarcorreo():
    return render_template("index.html")

@app.route("/detalleconcurso/<string:id>", methods=['GET'])
def detalleconcurso(id):
    if 'username' in session:
      Concurso = concurso.obtener_url(id) 
      con_par = propuesta.obtener_Propuesta_por_concurso(Concurso['Items'][0]['id_concurso']['S'])
      item = con_par['Items']
      if not item:
          print ('No hay participantes')
          return render_template("detalleconcurso.html", con_par = item,  Concurso=Concurso['Items'][0])
      return render_template("detalleconcurso.html", con_par = item,  Concurso=Concurso['Items'][0])
    return 'You are not logged in'

@app.route("/detallarconcurso/<string:id>", methods=['GET'])
def detallarconcurso(id):
    Concurso = concurso.obtener_url(id) 
    con_par = propuesta.obtener_Propuesta_por_concurso(Concurso['Items'][0]['id_concurso']['S'])
    return render_template("detallarconcurso.html", con_par = con_par['Items'], id = Concurso['Items'][0]['id_concurso']['S'], Concurso=Concurso['Items'][0])

# Iniciar el servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
