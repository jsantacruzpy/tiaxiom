import http.server
import socketserver
import subprocess
import os
import json
import time
from urllib.parse import parse_qs
from datetime import datetime, timedelta
import sys

# Paso 1: Verificar e instalar paquetes necesarios
def install_package(package_name):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])

# Verificar e instalar boto3
try:
    import boto3
except ImportError:
    install_package('boto3')
    import boto3

# Configuración de rutas y archivos
if os.name == 'nt':
    credentials_file = os.path.expanduser('~\\.aws\\credentials')
else:
    credentials_file = os.path.expanduser('~/.aws/credentials')

# Paso 2: Obtener información de Workspaces
def get_workspaces_info(profile):
    try:
        result = subprocess.run(['aws', 'workspaces', 'describe-workspaces', '--profile', profile], capture_output=True, text=True)
        return json.loads(result.stdout).get('Workspaces', [])
    except Exception as e:
        print(f'Error al obtener la información de Workspaces: {e}')
        return []

# Paso 3: Obtener información de AWS Health
def get_aws_health_info():
    try:
        client = boto3.client('health', region_name='us-east-1')
        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()
        response = client.describe_events(
            filter={
                'services': ['WORKSPACES'],
                'eventStatusCodes': ['open', 'resolved'],
                'startTime': start_time,
                'endTime': end_time,
            }
        )
        return response.get('events', [])
    except Exception as e:
        print(f'Error al obtener la información de AWS Health: {e}')
        return []

# Paso 4: Generar HTML para la página principal
def generate_html(workspaces, credentials_saved):
    vdi_count = len(workspaces)  # Contar la cantidad de VDI

    html = f"""
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Workspaces Info</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.27/jspdf.plugin.autotable.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .navbar {{ margin-bottom: 20px; background-color: #232f3e; }}
            .navbar-nav .nav-link {{ margin-right: 15px; color: white; }}
            .navbar .nav-link:hover {{ color: #e2e6ea; }}
            .navbar .btn {{ margin-left: 10px; background-color: #232f3e; color: white; border: none; }}
            .navbar .btn:hover {{ background-color: #1c1e22; }}
            .status-available {{ background-color: #d4edda; }}
            .status-impaired {{ background-color: #f8d7da; }}
            .status-pending {{ background-color: #fff3cd; }}
            .status-terminating {{ background-color: #d6d6d6; }}
            .status-suspended {{ background-color: #e2e3e5; }}
            .footer {{ margin-top: 20px; text-align: center; }}
            .navbar-expand-lg .navbar-nav {{ justify-content: center; }}
            .alert {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark">
            <a class="navbar-brand" href="/">
                <img src="https://www.tiaxiom.com.py/wp-content/uploads/2022/10/cropped-logo-final-colores-copy-1.png" alt="jh4n3r" style="width: 150px;">
            </a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav mx-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Inicio</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="export-csv">Exportar CSV</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="export-pdf">Exportar PDF</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="manual-query">Actualizar</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/config">Configuración</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/health">Estado de AWS Health</a>
                    </li>
                </ul>
            </div>
        </nav>
        <div class="container">
            <h1>Workspaces Info</h1>
            <p><strong>Cantidad de VDI existentes:</strong> {vdi_count}</p>  <!-- Añadido aquí -->
            <input type="text" id="search-input" class="form-control mb-3" placeholder="Busqueda multiples separadas por comas: user1,user2,user3">
            <table class="table table-bordered" id="workspaces-table">
                <thead>
                    <tr>
                        <th>Workspace ID</th>
                        <th>Directory ID</th>
                        <th>Estado</th>
                        <th>Usuarios</th>
                        <th>Bundle ID</th>
                        <th>Nombre de Equipo</th>
                        <th>IP</th>
                        <th>Protocolo</th>
                        <th>Tags</th>
                    </tr>
                </thead>
                <tbody>
    """
    for ws in workspaces:
        state = ws.get('State', 'UNKNOWN')
        state_class = 'status-unknown'
        if state == 'AVAILABLE':
            state_class = 'status-available'
        elif state == 'IMPAIRED':
            state_class = 'status-impaired'
        elif state == 'PENDING':
            state_class = 'status-pending'
        elif state == 'TERMINATING':
            state_class = 'status-terminating'
        elif state == 'SUSPENDED':
            state_class = 'status-suspended'
        html += f"""
        <tr class="{state_class}">
            <td>{ws.get('WorkspaceId', 'N/A')}</td>
            <td>{ws.get('DirectoryId', 'N/A')}</td>
            <td>{state}</td>
            <td>{ws.get('UserName', 'N/A')}</td>
            <td>{ws.get('BundleId', 'N/A')}</td>
            <td>{ws.get('ComputerName', 'N/A')}</td>
            <td>{ws.get('IpAddress', 'N/A')}</td>
            <td>{ws.get('WorkspaceProperties',).get('Protocols', 'N/A')}</td>
            <td>{ws.get('Tags', 'N/A')}</td>
        </tr>
        """
    html += """
                </tbody>
            </table>
        </div>
        <div class="footer">
            <p>&copy; jh4n3r - Tiaxiom.</p>
        </div>
        <script>
            function exportTableToCSV() {
                const rows = Array.from(document.querySelectorAll('table tr'));
                const csvContent = rows.map(row => {
                    const cols = Array.from(row.querySelectorAll('td, th'));
                    return cols.map(col => col.innerText).join(',');
                }).join('\\n');
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = 'workspaces-info.csv';
                link.click();
            }

            function exportTableToPDF() {
                const { jsPDF } = window.jspdf;
                const doc = new jsPDF();
                doc.autoTable({ html: '#workspaces-table' });
                doc.save('workspaces-info.pdf');
            }

            function manualQuery() {
                fetch('/manual-query')
                    .then(response => response.text())
                    .then(data => {
                        const newWindow = window.open();
                        newWindow.document.write(data);
                    });
            }

            document.getElementById('export-csv').addEventListener('click', exportTableToCSV);
            document.getElementById('export-pdf').addEventListener('click', exportTableToPDF);
            document.getElementById('manual-query').addEventListener('click', manualQuery);

            document.getElementById('search-input').addEventListener('input', function() {
            const searchTerms = this.value.toLowerCase().split(',').map(term => term.trim());
            const rows = document.querySelectorAll('#workspaces-table tbody tr');
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const match = searchTerms.some(searchTerm => 
                    Array.from(cells).some(cell => cell.textContent.toLowerCase().includes(searchTerm))
        );
        row.style.display = match ? '' : 'none';
    });
});
        </script>
    </body>
    </html>
    """
    return html


# Paso 5: Generar HTML para la página de configuración
def generate_html_config_page(message):
    return f"""
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Configuración de Credenciales</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .navbar {{ margin-bottom: 20px; background-color: #232f3e; }}
            .navbar-nav .nav-link {{ margin-right: 15px; color: white; }}
            .navbar .nav-link:hover {{ color: #e2e6ea; }}
            .navbar .btn {{ margin-left: 10px; background-color: #232f3e; color: white; border: none; }}
            .navbar .btn:hover {{ background-color: #1c1e22; }}
            .footer {{ margin-top: 20px; text-align: center; }}
            .navbar-expand-lg .navbar-nav {{ justify-content: center; }}
            .alert {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark">
            <a class="navbar-brand" href="/">
                <img src="https://www.tiaxiom.com.py/wp-content/uploads/2022/10/cropped-logo-final-colores-copy-1.png" alt="Tiaxiom" style="width: 150px;">
            </a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav mx-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Inicio</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="export-csv">Exportar CSV</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="export-pdf">Exportar PDF</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="manual-query">Actualizar</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/config">Configuración</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/health">Estado de AWS Health</a>
                    </li>
                </ul>
            </div>
        </nav>
        <div class="container">
            <h1>Configuración de Credenciales</h1>
            {f'<div class="alert alert-success">Configuración guardada correctamente</div>' if message == 'success' else ''}
             <div class="alert alert-info">Asegúrate de tener instalada la <a href="https://docs.aws.amazon.com/es_es/cli/latest/userguide/getting-started-install.html">AWS CLI versión 2</a> y tener un perfil configurado..</div>
            <form action="/save-config" method="post">
                <div class="mb-3">
                    <label for="access_key_id" class="form-label">Access Key ID</label>
                    <input type="text" class="form-control" id="access_key_id" name="access_key_id" required>
                </div>
                <div class="mb-3">
                    <label for="secret_access_key" class="form-label">Secret Access Key</label>
                    <input type="text" class="form-control" id="secret_access_key" name="secret_access_key" required>
                </div>
                <div class="mb-3">
                    <label for="session_token" class="form-label">Session Token</label>
                    <input type="text" class="form-control" id="session_token" name="session_token" required>
                </div>
                <button type="submit" class="btn btn-primary" name="action" value="save">Guardar Configuración</button>
                <button type="submit" class="btn btn-secondary" name="action" value="connect">Conectar SSO</button>
            </form>
             <div class="alert alert-info">Utilice el boton conectar SSO en la primera conexión.</div>
             <div class="alert alert-info">Guardar configuración para actualizar el access key, en caso de que haya caducado.</div>
            <a href="/">Volver a la página principal</a>
        </div>
          
        <div class="footer">
            <p>&copy; jh4n3r - Tiaxiom.</p>
        </div>
    </body>
    </html>
    """


# Paso 6: Generar HTML para la página de estado de AWS Health
def generate_html_health_page(events):
    html = f"""
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Estado de AWS Health</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .navbar {{ margin-bottom: 20px; background-color: #232f3e; }}
            .navbar-nav .nav-link {{ margin-right: 15px; color: white; }}
            .navbar .nav-link:hover {{ color: #e2e6ea; }}
            .navbar .btn {{ margin-left: 10px; background-color: #232f3e; color: white; border: none; }}
            .navbar .btn:hover {{ background-color: #1c1e22; }}
            .footer {{ margin-top: 20px; text-align: center; }}
            .navbar-expand-lg .navbar-nav {{ justify-content: center; }}
            .alert {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark">
            <a class="navbar-brand" href="/">
                <img src="https://www.tiaxiom.com.py/wp-content/uploads/2022/10/cropped-logo-final-colores-copy-1.png" alt="Tiaxiom" style="width: 150px;">
            </a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav mx-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Inicio</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="export-csv">Exportar CSV</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="export-pdf">Exportar PDF</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link btn" href="#" id="manual-query">Actualizar</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/config">Configuración</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/health">Estado de AWS Health</a>
                    </li>
                </ul>
            </div>
        </nav>
        <div class="container">
            <h1>Estado de AWS Health</h1>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>ID del Evento</th>
                        <th>Descripción</th>
                        <th>Estado</th>
                        <th>Fecha de Inicio</th>
                        <th>Fecha de Fin</th>
                    </tr>
                </thead>
                <tbody>
    """
    if not events:
        html += """
        <tr>
            <td colspan="5">No se reportaron errores en los últimos 7 días.</td>
        </tr>
        """
    else:
        for event in events:
            html += f"""
            <tr>
                <td>{event.get('arn', 'N/A')}</td>
                <td>{event.get('description', 'N/A')}</td>
                <td>{event.get('statusCode', 'N/A')}</td>
                <td>{event.get('startTime', 'N/A')}</td>
                <td>{event.get('endTime', 'N/A')}</td>
            </tr>
            """
    html += """
                </tbody>
            </table>
                        <p>Consulte el siguiente enlace para ver mas detalles. 
            <a href="https://health.aws.amazon.com/health/status" target="_blank"">AWS Health</a></p>
            
            <div>
            <a href="/">Volver a la página principal</a>
        </div></div>
        <div class="footer">
            <p>&copy; jh4n3r - Tiaxiom.</p>
        </div>
    </body>
    </html>
    """
    return html

# Paso 7: Guardar las credenciales en un archivo
def save_credentials(access_key_id, secret_access_key, session_token):
    try:
        os.makedirs(os.path.dirname(credentials_file), exist_ok=True)
        with open(credentials_file, 'w') as file:
            file.write(f"[default]\n")
            file.write(f"aws_access_key_id={access_key_id}\n")
            file.write(f"aws_secret_access_key={secret_access_key}\n")
            file.write(f"aws_session_token={session_token}\n")
        print("Credenciales guardadas correctamente.")
    except Exception as e:
        print(f"Error al guardar las credenciales: {e}")

# Manejador HTTP
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Página principal
            workspaces = get_workspaces_info('itau-ws')
            credentials_saved = os.path.exists(credentials_file)
            html = generate_html(workspaces, credentials_saved)
            if html:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_error(500, "Error al generar el contenido HTML.")
        elif self.path.startswith('/config'):
            # Página de configuración
            message = 'success' if 'message=success' in self.path else ''
            html = generate_html_config_page(message)
            if html:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_error(500, "Error al generar el contenido HTML.")
        elif self.path == '/manual-query':
            workspaces = get_workspaces_info('itau-ws')
            html = generate_html(workspaces, os.path.exists(credentials_file))
            if html:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_error(500, "Error al generar el contenido HTML.")
        elif self.path.startswith('/health'):
            # Página de estado de AWS Health
            events = get_aws_health_info()
            html = generate_html_health_page(events)
            if html:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_error(500, "Error al generar el contenido HTML.")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/save-config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)
            access_key_id = params.get('access_key_id', [''])[0]
            secret_access_key = params.get('secret_access_key', [''])[0]
            session_token = params.get('session_token', [''])[0]
            action = params.get('action', [''])[0]
            if action == 'save':
                save_credentials(access_key_id, secret_access_key, session_token)
                self.send_response(303)
                self.send_header('Location', '/config?message=success')
                self.end_headers()
            elif action == 'connect':
                # Ejecutar el comando aws sso login
                try:
                    subprocess.run(['powershell', '-Command', 'aws sso login --profile itau-ws'], check=True)
                    self.send_response(303)
                    self.send_header('Location', '/config?message=success')
                    self.end_headers()
                except subprocess.CalledProcessError:
                    self.send_error(500, "Error al ejecutar el comando de AWS CLI.")
        else:
            self.send_error(404, "Página no encontrada.")


# Configuración del servidor HTTP
PORT = 8991

with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
    print(f"Servidor corriendo en http://localhost:{PORT}/config")
    print(f"Servidor corriendo en http://127.0.0.1:{PORT}/config")
    httpd.serve_forever()
