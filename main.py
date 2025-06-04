from flask import Flask, render_template, request, send_file, url_for
from wireguard_tools import WireguardKey
import qrcode
import io
import base64
import ipaddress

app = Flask(__name__)

def generate_keys():
    private_key = WireguardKey.generate()
    public_key = private_key.public_key()
    return str(private_key), str(public_key)

def ip_add(ip, offset):
    return str(ipaddress.IPv4Address(ipaddress.IPv4Address(ip) + offset))

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    qr_img = None
    server_config = None

    if request.method == 'POST':
        try:
            mode = request.form['mode']
            endpoint = request.form['endpoint']
            port = request.form['port']
            allowed_ips = request.form['allowed_ips']
            iface_name = request.form.get('iface_name', 'wireguard')
            client_name = request.form.get('client_name', 'Cliente')
            client_ip = request.form.get('client_ip', '').strip()
            is_multi = request.form.get('multiple') == 'on'

            if not client_ip:
                return render_template('index.html', error="La IP del cliente es obligatoria.")

            if mode == 'new_server':
                server_private, server_public = generate_keys()
                interface_ip = request.form.get('interface_ip', '').strip()
                server_config = f"""/interface wireguard
add listen-port={port} name={iface_name} private-key="{server_private}"

/ip address
add address={interface_ip}/24 interface={iface_name}

/ip firewall filter
add chain=input protocol=udp dst-port={port} action=accept comment="Allow WireGuard"
"""
            else:
                server_public = request.form.get('server_public', '').strip()

            if is_multi:
                count = int(request.form['count'])
                for i in range(count):
                    ip = ip_add(client_ip, i)
                    priv, pub = generate_keys()
                    conf = f"""[Interface]
PrivateKey = {priv}
Address = {ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public}
AllowedIPs = {allowed_ips}
Endpoint = {endpoint}:{port}
PersistentKeepalive = 25
"""
                    mikrotik_cmd = f"""/interface wireguard peers
add allowed-address={ip}/32 interface={iface_name} public-key="{pub}" comment="{client_name}-{i+1}" respond=no
"""
                    qr = qrcode.make(conf)
                    buf = io.BytesIO()
                    qr.save(buf, format="PNG")
                    qr_b64 = base64.b64encode(buf.getvalue()).decode()

                    results.append({
                        'client_name': f"{client_name}-{i+1}",
                        'client_config': conf,
                        'mikrotik_peer_cmd': mikrotik_cmd,
                        'qr_img': qr_b64
                    })

            else:
                priv, pub = generate_keys()
                conf = f"""[Interface]
PrivateKey = {priv}
Address = {client_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public}
AllowedIPs = {allowed_ips}
Endpoint = {endpoint}:{port}
PersistentKeepalive = 25
"""
                mikrotik_cmd = f"""/interface wireguard peers
add allowed-address={client_ip}/32 interface={iface_name} public-key="{pub}" comment="{client_name}" respond=no
"""
                qr = qrcode.make(conf)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")
                qr_b64 = base64.b64encode(buf.getvalue()).decode()

                results.append({
                    'client_name': client_name,
                    'client_config': conf,
                    'mikrotik_peer_cmd': mikrotik_cmd,
                    'qr_img': qr_b64
                })

        except Exception as e:
            return render_template('index.html', error=str(e))

    return render_template('index.html', result=results, server_config=server_config)

@app.route('/download_conf')
def download_conf():
    client_name = request.args.get('name', 'cliente')
    client_name = client_name.replace(" ", "")
    conf_data = request.args.get('data', '')
    return send_file(io.BytesIO(conf_data.encode()), download_name=f"{client_name}.conf", as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
