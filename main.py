from flask import Flask, render_template, request, send_file
from wireguard_tools import WireguardKey
import qrcode
import io, base64

app = Flask(__name__)

def generate_keys():
    private_key = WireguardKey.generate()
    public_key = private_key.public_key()
    return str(private_key), str(public_key)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    qr_img = None
    server_config = None
    download_conf = None

    if request.method == 'POST':
        mode = request.form['mode']
        endpoint = request.form['endpoint']
        port = request.form['port']
        allowed_ips = request.form['allowed_ips']
        iface_name = request.form.get('iface_name', 'wireguard')
        client_name = request.form.get('client_name', 'Cliente')
        
        if mode == 'new_server':
            server_private, server_public = generate_keys()
            interface_ip = request.form['interface_ip']

            server_config = f"""/interface wireguard
add listen-port={port} name={iface_name} private-key="{server_private}"

/ip address
add address={interface_ip}/24 interface={iface_name}

/ip firewall filter
add chain=input protocol=udp dst-port={port} action=accept comment="Allow WireGuard"
"""
        else:
            server_public = request.form['server_public']

        client_ip = request.form['client_ip']
        client_private, client_public = generate_keys()

        client_config = f"""[Interface]
PrivateKey = {client_private}
Address = {client_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public}
AllowedIPs = {allowed_ips}
Endpoint = {endpoint}:{port}
PersistentKeepalive = 25
"""

        mikrotik_peer_cmd = f"""/interface wireguard peers
add allowed-address={client_ip}/32 interface={iface_name} public-key="{client_public}" comment="{client_name}"
"""

        qr = qrcode.make(client_config)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_img = base64.b64encode(buffer.getvalue()).decode()

        result = {
            'client_config': client_config,
            'mikrotik_peer_cmd': mikrotik_peer_cmd
        }

        # para descarga directa del conf
        download_conf = io.BytesIO(client_config.encode())
        download_conf.name = f"{client_name}.conf"
        download_conf.seek(0)

    return render_template('index.html', result=result, qr_img=qr_img, server_config=server_config, download_conf=download_conf)

@app.route('/download_conf')
def download_conf():
    client_name = request.args.get('name', 'cliente')
    conf_data = request.args.get('data', '')
    return send_file(io.BytesIO(conf_data.encode()), download_name=f"{client_name}.conf", as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)