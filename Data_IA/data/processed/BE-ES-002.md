- Getting Help

- zh-hans

- sv

- pt-br

- pl

- ko

- ja

- it

- id

- fr

- en

- el

- dev

- 6.1

- 6.0

- 5.1

- 5.0

- 4.2

- 4.1

- 4.0

- 3.2

- 3.1

- 3.0

- 2.2

- 2.1

- 2.0

- 1.11

- 1.10

# Escribiendo su primera aplicación en Django, parte 1

Aprendamos mediante el ejemplo.

A través de este tutorial le mostraremos cómo crear una aplicación de encuestas básica.

Consistirá de dos partes:

- Un sitio público que le permite a las personas ver sondeos y votar en ellos.

Un sitio público que le permite a las personas ver sondeos y votar en ellos.

- Un sitio administrativo que le permite añadir, modificar y borrar sondeos.

Un sitio administrativo que le permite añadir, modificar y borrar sondeos.

Asumiremos que ya ha instalado Django . Puede ver si Django está instalado, así como su versión, ejecutando el siguiente comando (señalado por el prefijo $):

```text
$ python -m django --version
```

```text
...\> py -m django --version
```

Si Django está instalado, debería ver la versión de su instalación. Si no es así, obtendrá un error indicando que «No existe el módulo llamado Django».

This tutorial is written for Django 5.2, which supports Python 3.10 and
later. If the Django version doesn’t match, you can refer to the tutorial for
your version of Django by using the version switcher at the bottom right corner
of this page, or update Django to the newest version. If you’re using an older
version of Python, check ¿Qué versión de Python puedo usar con Django? to find a compatible
version of Django.

Dónde obtener ayuda:

Si tiene problemas para seguir este tutorial, diríjase a la sección Obteniendo ayuda del FAQ.

## Creando un proyecto

Si esta es la primera vez que utiliza Django, tendrá que hacerse cargo de ciertas configuraciones iniciales. Concretamente, tendrá que autogenerar un código que establezca un Django project – un conjunto de ajustes para una instancia de Django, incluida la configuración de la base de datos, opciones específicas de Django y configuraciones específicas de la aplicación.

From the command line, cd into a directory where you’d like to store your
code and create a new directory named djangotutorial . (This directory name
doesn’t matter to Django; you can rename it to anything you like.)

`cd`

`djangotutorial`

```text
$ mkdir djangotutorial
```

```text
...\> mkdir djangotutorial
```

Then, run the following command to bootstrap a new Django project:

```text
$ django-admin startproject mysite djangotutorial
```

```text
...\> django-admin startproject mysite djangotutorial
```

This will create a project called mysite inside the djangotutorial directory. If it didn’t work, see Problemas ejecutando django-admin .

`mysite`

`djangotutorial`

Nota

Tendrá que evitar darle nombres a sus proyectos que sean iguales a los de otros componentes integrados de Python o Django. En particular, esto quiere decir que debe evitar usar nombres como django (que entrará en conflicto con Django mismo) o test (que entrará en conflicto con un paquete interno de Python).

`django`

`test`

Veamos lo que el comando startproject creó:

`startproject`

```text
djangotutorial/
    manage.py
    mysite/
        __init__.py
        settings.py
        urls.py
        asgi.py
        wsgi.py
```

Estos archivos son:

- manage.py : Una utilidad de la línea de comandos que le permite interactuar con este proyecto Django de diferentes formas. Puede leer todos los detalles sobre manage.py en django-admin and manage.py .

manage.py : Una utilidad de la línea de comandos que le permite interactuar con este proyecto Django de diferentes formas. Puede leer todos los detalles sobre manage.py en django-admin and manage.py .

`manage.py`

`manage.py`

- mysite/ : A directory that is the actual Python package for your
project. Its name is the Python package name you’ll need to use to import
anything inside it (e.g. mysite.urls ).

mysite/ : A directory that is the actual Python package for your
project. Its name is the Python package name you’ll need to use to import
anything inside it (e.g. mysite.urls ).

`mysite/`

`mysite.urls`

- mysite/__init__.py : Un archivo vacío que le indica a Python que este directorio debería ser considerado como un paquete Python. Si usted es un principiante lea más sobre los paquetes en la documentación oficial de Python.

mysite/__init__.py : Un archivo vacío que le indica a Python que este directorio debería ser considerado como un paquete Python. Si usted es un principiante lea más sobre los paquetes en la documentación oficial de Python.

`mysite/__init__.py`

- mysite/settings.py : Ajustes/configuración para este proyecto Django. Django settings le indicará todo sobre cómo funciona la configuración.

mysite/settings.py : Ajustes/configuración para este proyecto Django. Django settings le indicará todo sobre cómo funciona la configuración.

`mysite/settings.py`

- mysite/urls.py : Las declaraciones URL para este proyecto Django; una «tabla de contenidos» de su sitio basado en Django. Puede leer más sobre las URLs en URL dispatcher .

mysite/urls.py : Las declaraciones URL para este proyecto Django; una «tabla de contenidos» de su sitio basado en Django. Puede leer más sobre las URLs en URL dispatcher .

`mysite/urls.py`

- mysite/asgi.py : An entry-point for ASGI-compatible web servers to
serve your project. See How to deploy with ASGI for more details.

mysite/asgi.py : An entry-point for ASGI-compatible web servers to
serve your project. See How to deploy with ASGI for more details.

`mysite/asgi.py`

- mysite/wsgi.py : Un punto de entrada para que los servidores web compatibles con WSGI puedan servir su proyecto. Consulte :doc: ` /howto/deployment/wsgi/index`para más detalles.

mysite/wsgi.py : Un punto de entrada para que los servidores web compatibles con WSGI puedan servir su proyecto. Consulte :doc: ` /howto/deployment/wsgi/index`para más detalles.

`mysite/wsgi.py`

## El servidor de desarrollo

Let’s verify your Django project works. Change into the djangotutorial directory, if you haven’t already, and run the following commands:

`djangotutorial`

```text
$ python manage.py runserver
```

```text
...\> py manage.py runserver
```

Verá la siguiente salida en la línea de comandos:

```text
Performing system checks...

System check identified no issues (0 silenced).

You have unapplied migrations; your app may not work properly until they are applied.
Run 'python manage.py migrate' to apply them.

diciembre 02, 2025 - 15:50:53
Django version 5.2, using settings 'mysite.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.

WARNING: This is a development server. Do not use it in a production setting. Use a production WSGI or ASGI server instead.
For more information on production servers see: https://docs.djangoproject.com/en/5.2/howto/deployment/
```

Nota

Ignore por ahora la advertencia sobre las migraciones de bases de datos sin aplicar, nos ocuparemos de la base de datos dentro de poco.

Now that the server’s running, visit http://127.0.0.1:8000/ with your web
browser. You’ll see a «Congratulations!» page, with a rocket taking off.
It worked!

You’ve started the Django development server, a lightweight web server written
purely in Python. We’ve included this with Django so you can develop things
rapidly, without having to deal with configuring a production server – such as
Apache – until you’re ready for production.

Now’s a good time to note: don’t use this server in anything resembling a
production environment. It’s intended only for use while developing. (We’re in
the business of making web frameworks, not web servers.)

(To serve the site on a different port, see the runserver reference.)

`runserver`

Recarga automática del comando runserver

`runserver`

El servidor de desarrollo recarga de forma automática el código Python para cada petición cuando sea necesario. No es necesario reiniciar el servidor para que los cambios de código surtan efecto. Sin embargo, algunas acciones como la adición de archivos no provoca un reinicio, por lo que tendrá que reiniciar el servidor en estos casos.

## Creando la aplicación encuestas

Ahora que su entorno (un «proyecto») se ha configurado, ya está listo para empezar a trabajar.

Cada aplicación que usted escribe en Django consiste en un paquete de Python que sigue una determinada convención. Django tiene una utilidad que genera automáticamente la estructura básica de directorios de una aplicación, por lo que usted puede centrarse en la escritura de código en lugar de crear directorios.

Proyectos vs. aplicaciones

What’s the difference between a project and an app? An app is a web
application that does something – e.g., a blog system, a database of
public records or a small poll app. A project is a collection of
configuration and apps for a particular website. A project can contain
multiple apps. An app can be in multiple projects.

Your apps can live anywhere in your Python path . In
this tutorial, we’ll create our poll app inside the djangotutorial folder.

`djangotutorial`

Para crear su aplicación, asegúrese de que está en el mismo directorio que el archivo manage.py y escriba este comando:

`manage.py`

```text
$ python manage.py startapp polls
```

```text
...\> py manage.py startapp polls
```

Esto creará un directorio polls , que se presenta de la siguiente manera:

`polls`

```text
polls/
    __init__.py
    admin.py
    apps.py
    migrations/
        __init__.py
    models.py
    tests.py
    views.py
```

Esta estructura de directorios almacenará la aplicación encuesta.

## Escriba su primera vista

Vamos a escribir la primera vista. Abra el archivo polls/views.py y ponga el siguiente código Python en ella:

`polls/views.py`

`polls/views.py`

```text
from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello, world. You're at the polls index.")
```

This is the most basic view possible in Django. To access it in a browser, we
need to map it to a URL - and for this we need to define a URL configuration,
or «URLconf» for short. These URL configurations are defined inside each
Django app, and they are Python files named urls.py .

`urls.py`

To define a URLconf for the polls app, create a file polls/urls.py with the following content:

`polls`

`polls/urls.py`

`polls/urls.py`

```text
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
]
```

Su directorio de aplicaciones ahora debería verse asi:

```text
polls/
    __init__.py
    admin.py
    apps.py
    migrations/
        __init__.py
    models.py
    tests.py
    urls.py
    views.py
```

The next step is to configure the root URLconf in the mysite project to
include the URLconf defined in polls.urls . To do this, add an import for django.urls.include in mysite/urls.py and insert an include() in the urlpatterns list, so you have:

`mysite`

`polls.urls`

`django.urls.include`

`mysite/urls.py`

`include()`

`urlpatterns`

`mysite/urls.py`

```text
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("polls/", include("polls.urls")),
    path("admin/", admin.site.urls),
]
```

The path() function expects at least two arguments: route and view .
The include() function allows referencing other URLconfs.
Whenever Django encounters include() , it chops off whatever
part of the URL matched up to that point and sends the remaining string to the
included URLconf for further processing.

`path()`

`route`

`view`

`include()`

`include()`

La idea detrás de include() es facilitar la conexión y ejecución inmediata de las URLs. Dado que las encuestas están en su propia URLconf ( polls/urls.py ) se pueden ubicar en «/polls/», «/fun_polls /», «/content/polls/» o en cualquier otra ruta raíz , y la aplicación todavía seguirá funcionando.

`include()`

`polls/urls.py`

Cuándo utilizar include()

`include()`

You should always use include() when you include other URL patterns.
The only exception is admin.site.urls , which is a pre-built URLconf
provided by Django for the default admin site.

`include()`

`admin.site.urls`

Ahora tiene una vista index vinculada en los URLconf. Compruebe su funcionamiento con el siguiente comando:

`index`

```text
$ python manage.py runserver
```

```text
...\> py manage.py runserver
```

Vaya a http://localhost:8000/polls/ en su navegador, y usted debería ver el texto « Hello, world. You’re at the polls index. » el cual definió en la vista index .

`index`

¿Página no encotrada?

Si usted obtiene aquí una página de error, revisee que usted este llendo a la dirección URL http://localhost:8000/polls/ y no a la dirección URL http://localhost:8000/ .

Cuando se familiarice con el flujo básico de solicitud y respuesta, lea la parte 2 del presente tutorial para empezar a trabajar con la base de datos.